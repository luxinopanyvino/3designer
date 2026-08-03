# PrintCAD Organic — microservicio foto → malla neuronal

Servicio FastAPI independiente que reconstruye una malla 3D a partir de una foto. Vive en su propio proyecto uv porque su stack (PyTorch cu128, transformers) es pesado e incompatible con el backend principal.

Motores (variable `ORGANIC_ENGINE`):

- **`trellis2`** (por defecto): [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2) `TRELLIS.2-4B`. Aristas más definidas y topología más limpia que v1. Solo se carga y ejecuta la mitad de *forma* del modelo: la etapa de materiales PBR es peso muerto para impresión monomaterial.
- **`trellis`**: [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) `image-large`, el motor anterior. ~6 GB de VRAM residentes, ~1-2 min por pieza en una RTX 5060 Ti.
- **`triposr`**: el motor más antiguo (stabilityai/TripoSR), más rápido y ligero pero mucho menos detallado.

## Setup (una vez)

```powershell
cd organic

# Los repos no se distribuyen en PyPI; se vendorizan (no se commitean, ver .gitignore raíz)
git clone https://github.com/microsoft/TRELLIS.2.git vendor/TRELLIS.2
git -C vendor/TRELLIS.2 checkout 75fbf01                                   # commit probado

# Solo si quieres los motores antiguos como respaldo:
git clone https://github.com/microsoft/TRELLIS.git vendor/TRELLIS
git -C vendor/TRELLIS checkout 442aa1e
git -C vendor/TRELLIS submodule update --init trellis/representations/mesh/flexicubes
git clone https://github.com/VAST-AI-Research/TripoSR.git vendor/TripoSR
git -C vendor/TripoSR checkout 107cefd

uv sync   # descarga PyTorch cu128 (~2 GB)
```

### Extensiones CUDA de TRELLIS.2

TRELLIS.2 necesita cuatro extensiones nativas (`o_voxel`, `cumesh`, `flex_gemm`, `nvdiffrast`) que no están en PyPI. Hay wheels precompiladas para Windows / Python 3.12 / sm_120 (Blackwell) en [visualbruno/ComfyUI-Trellis2](https://github.com/visualbruno/ComfyUI-Trellis2):

```powershell
mkdir vendor/wheels
$base = "https://github.com/visualbruno/ComfyUI-Trellis2/raw/main/wheels/Windows/Torch2100/CUDA%2013.1"
foreach ($w in "cumesh-0.0.1", "flex_gemm-1.0.0", "o_voxel-0.0.1", "nvdiffrast-0.4.0") {
    $f = "$w-cp312-cp312-win_amd64.whl"
    curl.exe -sL -o "vendor/wheels/$f" "$base/$f"
}
uv pip install --no-deps vendor/wheels/*.whl
```

> **`uv sync` desinstala estas wheels** (no están declaradas en `pyproject.toml`, porque `vendor/` no se commitea). Repite el `uv pip install` después de cada `uv sync`.

Detalles que cuestan tiempo si se descubren a mano:

- **La versión de torch está clavada en `2.10.0`.** Las wheels se compilan contra esa ABI de libtorch y fallan con cualquier otra (error `DLL load failed ... _C`). No la subas sin recompilarlas.
- **cu128, no cu130**, aunque las wheels se compilaran con el toolkit CUDA 13.1: las extensiones no enlazan runtime de CUDA propio, así que les da igual cuál traiga torch, mientras que `spconv` (motor `trellis` v1) no tiene build para CUDA 13 y se rompería.
- Hay otro juego de wheels en `PixWizardry/AI_Trellis2-WHLs-RTX-PRO-6000` que dice ser para torch 2.10 pero **no** casa con el torch oficial: falla con `ERROR_PROC_NOT_FOUND`.

### Acceso a DINOv3 (obligatorio)

El condicionador de imagen de TRELLIS.2 es `facebook/dinov3-vitl16-pretrain-lvd1689m`, un repo **gated con aprobación manual** de Meta. Sin acceso, el arranque del motor falla con `OSError: You are trying to access a gated repo`.

1. Pide acceso en <https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m> y espera la aprobación.
2. Autentícate: `uv run huggingface-cli login` (o exporta `HF_TOKEN`).

Los demás pesos se descargan solos en el primer `/generate` y se cachean en `~/.cache/huggingface`: TRELLIS.2 rama de forma ~8.2 GB (los checkpoints de textura no se descargan), DINOv3 ~1.1 GB.

## Arranque

```powershell
cd organic
uv run uvicorn service:app --port 8001
# o con un motor antiguo:
$env:ORGANIC_ENGINE = "trellis"; uv run uvicorn service:app --port 8001
```

El backend principal lo detecta vía `/health` y el frontend habilita el modo "🗿 Orgánico (foto)".

## Resolución y VRAM

`TRELLIS2_PIPELINE` elige el tipo de pipeline: `512` (por defecto), `1024`, `1024_cascade` o `1536_cascade`. Upstream pide 24 GB y esta máquina tiene 16 GB, así que el valor por defecto es el más barato.

Si quieres más detalle, sube el valor (`$env:TRELLIS2_PIPELINE = "1024_cascade"`). Con cualquier valor por encima de `512`, el motor **reintenta una vez a `512`** si se queda sin memoria, en lugar de devolver un 500.

## Cómo corre TRELLIS en Windows sin compilar CUDA

Ambas versiones piden flash-attn o xformers para la atención dispersa, que no aceptan el backend `sdpa` nativo. Este servicio los sustituye con shims locales:

- `xformers/` — reimplementa `memory_efficient_attention` + `BlockDiagonalMask` sobre la SDPA de torch. La atención *por ventanas* de TRELLIS.2 genera miles de bloques por capa, así que esa ruta usa un tensor anidado *jagged*: una sola llamada SDPA, sin relleno. Medido sobre una capa de 2000 bloques es ~5× más rápido que iterar bloque a bloque y gasta menos memoria que rellenar hasta la ventana más larga (rellenar cuesta varios GB cuando la distribución es desigual).
- `kaolin/` — solo `check_tensor`, el validador de shapes que importa FlexiCubes (v1).
- `torchmcubes.py` — marching cubes de scikit-image para TripoSR.
- `open3d` se stubbea en memoria para v1 (solo lo importa su pipeline texto→3D, que no se usa). TRELLIS.2 no lo necesita: sus pipelines se importan de forma perezosa.

## Notas

- Una reconstrucción cada vez (lock): la VRAM no da para dos.
- TRELLIS.2 corre con `low_vram=True`: cada etapa sube su modelo a la GPU y lo baja al terminar.
- La malla se decima a ≤500k caras antes de exportar (con CuMesh en GPU para `trellis2`, con `fast-simplification` en CPU para v1) y se le tapan agujeros.
- Devuelve STL crudo; el backend principal lo repara (componente mayor, agujeros, normales), lo escala y lo apoya en la cama.
- La semilla es aleatoria en cada petición: reenviar la misma foto da variantes distintas.
