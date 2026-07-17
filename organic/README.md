# PrintCAD Organic — microservicio foto → malla neuronal

Servicio FastAPI independiente que reconstruye una malla 3D a partir de una foto. Vive en su propio proyecto uv porque su stack (PyTorch cu128, transformers) es pesado e incompatible con el backend principal.

Motores (variable `ORGANIC_ENGINE`):

- **`trellis`** (por defecto): [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) `image-large`. Calidad muy superior; ~6 GB de VRAM residentes, ~1-2 min por pieza en una RTX 5060 Ti.
- **`triposr`**: el motor antiguo (stabilityai/TripoSR), más rápido y ligero pero mucho menos detallado.

## Setup (una vez)

```powershell
cd organic

# Los repos no se distribuyen en PyPI; se vendorizan (no se commitean, ver .gitignore raíz)
git clone https://github.com/microsoft/TRELLIS.git vendor/TRELLIS
git -C vendor/TRELLIS checkout 442aa1e                                     # commit probado
git -C vendor/TRELLIS submodule update --init trellis/representations/mesh/flexicubes

# Solo si quieres el motor antiguo como respaldo:
git clone https://github.com/VAST-AI-Research/TripoSR.git vendor/TripoSR
git -C vendor/TripoSR checkout 107cefd

uv sync   # descarga PyTorch cu128 (~6 GB) — obligatorio cu128+ para RTX 5060 Ti (sm_120)
```

Los pesos se descargan de Hugging Face en el primer `/generate` y se cachean en `~/.cache/huggingface`: TRELLIS-image-large ~4.5 GB + DINOv2 (torch.hub) ~1.2 GB. TripoSR ~1.4 GB.

## Arranque

```powershell
cd organic
uv run uvicorn service:app --port 8001
# o con el motor antiguo:
$env:ORGANIC_ENGINE = "triposr"; uv run uvicorn service:app --port 8001
```

El backend principal lo detecta vía `/health` y el frontend habilita el modo "🗿 Orgánico (foto)".

## Cómo corre TRELLIS en Windows sin compilar CUDA

TRELLIS oficialmente pide flash-attn/xformers, kaolin, nvdiffrast, etc. Este servicio solo usa la salida de **malla** (sin texturizado ni render), lo que reduce las dependencias nativas a `spconv-cu126` (wheel precompilado; sus kernels PTX se JIT-compilan para sm_120). El resto se resuelve con shims locales:

- `xformers/` — reimplementa `memory_efficient_attention` + `BlockDiagonalMask` sobre la SDPA nativa de torch (la atención densa ya usa `ATTN_BACKEND=sdpa`).
- `kaolin/` — solo `check_tensor`, el validador de shapes que importa FlexiCubes.
- `torchmcubes.py` — marching cubes de scikit-image para TripoSR.
- `open3d` se stubbea en memoria (solo lo importa el pipeline texto→3D, que no se usa).

## Notas

- Una reconstrucción cada vez (lock): la VRAM se comparte con Ollama. Con TRELLIS + qwen3-vl cargados a la vez en 16 GB puede haber apuros; si ves OOM, descarga el modelo de Ollama (`ollama stop qwen3-vl:8b`) antes de generar.
- La malla se decima a ≤500k caras (`fast-simplification`) antes de exportar.
- Devuelve STL crudo; el backend principal lo repara (componente mayor, agujeros, normales), lo escala y lo apoya en la cama.
- La semilla es aleatoria en cada petición: reenviar la misma foto da variantes distintas.
