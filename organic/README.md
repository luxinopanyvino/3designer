# PrintCAD Organic — microservicio foto → malla neuronal

Servicio FastAPI independiente que reconstruye una malla 3D (TripoSR) a partir de una foto. Vive en su propio proyecto uv porque su stack (PyTorch cu128, transformers) es pesado e incompatible con el backend principal.

## Setup (una vez)

```powershell
cd organic

# TripoSR no se distribuye en PyPI; se vendoriza el repo (no se commitea, ver .gitignore raíz)
git clone https://github.com/VAST-AI-Research/TripoSR.git vendor/TripoSR
git -C vendor/TripoSR checkout 107cefd   # commit probado

uv sync   # descarga PyTorch cu128 (~6 GB) — obligatorio cu128+ para RTX 5060 Ti (sm_120)
```

Los pesos del modelo (`stabilityai/TripoSR`, ~1.4 GB) se descargan de Hugging Face en el primer `/generate` y se cachean en `~/.cache/huggingface`.

## Arranque

```powershell
cd organic
uv run uvicorn service:app --port 8001
```

El backend principal lo detecta vía `/health` y el frontend habilita el modo "🗿 Orgánico (foto)".

## Notas

- `torchmcubes.py` es un shim local: sustituye al paquete `torchmcubes` (que exige compilar C++/CUDA en Windows) por el marching cubes de scikit-image.
- Una reconstrucción cada vez (lock): la VRAM se comparte con Ollama.
- Devuelve STL crudo; el backend principal lo repara (componente mayor, agujeros, normales), lo escala y lo apoya en la cama.
