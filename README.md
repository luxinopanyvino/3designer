# PrintCAD — diseño 3D imprimible con IA local

Herramienta web para diseñar piezas de impresión 3D a partir de prompts en lenguaje natural, usando modelos locales de Ollama. El LLM genera código [CadQuery](https://cadquery.readthedocs.io/) paramétrico que se ejecuta en un sandbox y produce sólidos exactos y estancos, listos para el slicer.

```
Prompt ──► qwen2.5-coder:14b (Ollama) ──► código CadQuery ──► sandbox ──► STL/STEP/GLB
  ▲                                                                          │
  └── "hazlo 10 mm más ancho" (el código es la fuente de verdad) ◄── visor 3D
```

## Requisitos

- Windows (probado en Windows 11) · [uv](https://docs.astral.sh/uv/) · Node 20+
- [Ollama](https://ollama.com) con el modelo de código: `ollama pull qwen2.5-coder:14b` (~9 GB, cabe en 16 GB de VRAM)

## Arranque

```powershell
# Terminal 1 — backend (uv instala Python 3.12 y dependencias automáticamente)
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev        # abre http://localhost:5173
```

## Uso

1. Describe la pieza: *"una caja de 80x60x30 mm con paredes de 2 mm"*.
2. El modelo aparece en el visor (cama de 220×220 mm, 1 unidad = 1 mm) con dimensiones, volumen y avisos de imprimibilidad (estanqueidad, voladizos >45°, tamaño de cama).
3. Refínalo por chat: *"hazla 10 mm más ancha"*, *"añade dos agujeros M3 separados 20 mm"*. Cada iteración crea una versión nueva; el código CadQuery es siempre la fuente de verdad ("Ver código" en cada resultado).
4. Exporta STL (binario) o STEP (B-rep exacto) con los botones del visor.

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
| `frontend/` | React + react-three-fiber: visor Z-up, chat con streaming de código, export |

Los datos de sesión viven en `backend/data/sessions/{id}/` (JSON + una carpeta inmutable por versión) y sobreviven reinicios.

**Nota de seguridad**: el sandbox (AST + subprocess + timeout) es pragmático para una herramienta local personal; no es una frontera de seguridad contra un modelo hostil.

## Configuración

Variables de entorno con prefijo `PRINTCAD_` (ver `backend/app/config.py`): `PRINTCAD_MODEL_CODE` (por defecto `qwen2.5-coder:14b` — evita modelos >16 GB como qwen3.6, desbordan la VRAM), `PRINTCAD_BED_SIZE_MM`, `PRINTCAD_EXEC_TIMEOUT_S`, `PRINTCAD_OLLAMA_HOST`.

## Tests

```powershell
cd backend
uv run pytest        # sandbox, seguridad AST, mallas y API (sin LLM)
```

## Hoja de ruta

- **Fase 2 — imagen → CAD**: subir una foto de una pieza; `qwen3-vl:8b` extrae forma/características en JSON y alimenta la generación de código (plantilla `vision_analyze.md` ya incluida).
- **Fase 3 — formas orgánicas**: TripoSR/Hunyuan3D-2 (PyTorch cu128+, obligatorio para la RTX 5060 Ti) como servicio aparte para foto → malla orgánica, con reparación trimesh.
- Gizmos de edición manual, operaciones booleanas entre piezas y panel de parámetros editables.
