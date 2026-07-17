# PrintCAD — diseño 3D imprimible con IA local

Herramienta web para diseñar piezas de impresión 3D a partir de prompts en lenguaje natural o fotos de referencia, usando modelos locales de Ollama. El LLM genera código [CadQuery](https://cadquery.readthedocs.io/) paramétrico que se ejecuta en un sandbox y produce sólidos exactos y estancos, listos para el slicer.

```
Prompt ──► qwen2.5-coder:14b (Ollama) ──► código CadQuery ──► sandbox ──► STL/STEP/GLB
  ▲                                                                          │
  └── "hazlo 10 mm más ancho" (el código es la fuente de verdad) ◄── visor 3D
```

## Requisitos

- Windows (probado en Windows 11) · [uv](https://docs.astral.sh/uv/) · Node 20+
- [Ollama](https://ollama.com) con el modelo de código: `ollama pull qwen2.5-coder:14b` (~9 GB, cabe en 16 GB de VRAM)
- Opcional, para imagen→CAD: `ollama pull qwen3-vl:8b` (Ollama alterna ambos modelos en VRAM automáticamente)
- Opcional, para el modo orgánico (foto → malla neuronal): ver [organic/README.md](organic/README.md) (PyTorch cu128, ~6 GB)

## Arranque

```powershell
# Terminal 1 — backend (uv instala Python 3.12 y dependencias automáticamente)
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev        # abre http://localhost:5173

# Terminal 3 (opcional) — servicio orgánico, tras el setup de organic/README.md
cd organic
uv run uvicorn service:app --port 8001
```

O todo a la vez con `script.bat` desde la raíz.

## Uso

1. Describe la pieza: *"una caja de 80x60x30 mm con paredes de 2 mm"*.
2. El modelo aparece en el visor (cama de 220×220 mm, 1 unidad = 1 mm) con dimensiones, volumen y avisos de imprimibilidad (estanqueidad, voladizos >45°, tamaño de cama).
3. Refínalo por chat: *"hazla 10 mm más ancha"*, *"añade dos agujeros M3 separados 20 mm"*. Cada iteración crea una versión nueva; el código CadQuery es siempre la fuente de verdad ("Ver código" en cada resultado).
4. Exporta STL (binario) o STEP (B-rep exacto) con los botones del visor.
5. **Imagen → CAD**: adjunta una foto de una pieza con el botón 📷; `qwen3-vl:8b` la analiza y extrae un brief estructurado (tipo de pieza, agujeros, proporciones) que alimenta la generación. Tu texto aporta las dimensiones reales: *"la pieza de la foto, diámetro exterior 30 mm"*.
6. **Modo orgánico** (🗿, requiere el servicio de `organic/`): para figuras/esculturas que el CAD paramétrico no puede expresar. Adjunta una foto y elige el tamaño (mm del eje mayor); TripoSR reconstruye la malla y el backend la repara (componente mayor, agujeros, normales) y la apoya en la cama. Exporta STL/3MF — no hay STEP ni "Ver código": una malla neuronal no tiene B-rep.

Prueba sin frontend:

```powershell
cd backend
uv run python scripts\cli_generate.py "una escuadra en L con dos agujeros M4"
```

## Arquitectura

| Componente | Descripción |
|---|---|
| `backend/app/services/generation.py` | Orquestador: LLM → chequeo AST → sandbox → validación de malla, con bucle de autocorrección (3 intentos; el traceback vuelve al LLM) |
| `backend/app/sandbox/runner.py` | Subprocess aislado con timeout: ejecuta el código generado, exporta STL/STEP |
| `backend/app/services/code_safety.py` | Allowlist AST: solo `cadquery`, `math`, `numpy`; sin I/O ni acceso al sistema |
| `backend/app/services/mesh_service.py` | trimesh: STL→GLB para el visor, watertight, dimensiones, voladizos |
| `backend/app/prompts/` | Prompt del sistema con few-shots + chuleta CadQuery; plantillas generate/refine/repair |
| `backend/app/routers/` | FastAPI: sesiones, SSE de progreso, export, health |
| `backend/app/services/organic.py` | Cliente del servicio orgánico + reparación/normalizado de malla (trimesh) |
| `organic/` | Microservicio aparte (uv propio): TripoSR + PyTorch cu128, foto → STL en `:8001` |
| `frontend/` | React + react-three-fiber: visor Z-up, chat con streaming de código, export |

Los datos de sesión viven en `backend/data/sessions/{id}/` (JSON + una carpeta inmutable por versión) y sobreviven reinicios.

**Nota de seguridad**: el sandbox (AST + subprocess + timeout) es pragmático para una herramienta local personal; no es una frontera de seguridad contra un modelo hostil.

## Configuración

Variables de entorno con prefijo `PRINTCAD_` (ver `backend/app/config.py`): `PRINTCAD_MODEL_CODE` (por defecto `qwen2.5-coder:14b` — evita modelos >16 GB como qwen3.6, desbordan la VRAM), `PRINTCAD_BED_SIZE_MM`, `PRINTCAD_EXEC_TIMEOUT_S`, `PRINTCAD_OLLAMA_HOST`, `PRINTCAD_ORGANIC_SERVICE_URL` (por defecto `http://localhost:8001`), `PRINTCAD_ORGANIC_DEFAULT_SIZE_MM`.

## Tests

```powershell
cd backend
uv run pytest        # sandbox, seguridad AST, mallas y API (sin LLM)
```

## Hoja de ruta

- Gizmos de edición manual, operaciones booleanas entre piezas y panel de parámetros editables.
- Hunyuan3D-2 como alternativa de mayor calidad a TripoSR en el servicio orgánico.
