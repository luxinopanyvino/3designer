# PrintCAD — de una foto a pieza 3D imprimible o plano 2D DXF

Herramienta web local con dos casos de uso, ambos a partir de una imagen (+ prompt opcional):

```
Foto ──► 🗿 3D  ──► TRELLIS (reconstrucción neuronal) ──► reparación de malla ──► STL/3MF
Foto ──► 📐 2D  ──► OpenCV (contornos + agujeros) ──► DXF (ezdxf) + preview SVG
                    └── prompt opcional: medida real ("ancho 60 mm") y limpieza con IA
```

## Requisitos

- Windows (probado en Windows 11) · [uv](https://docs.astral.sh/uv/) · Node 20+
- Para el modo 3D: el servicio orgánico de `organic/` (PyTorch cu128, ~6 GB) — ver [organic/README.md](organic/README.md)
- Opcional, para la limpieza 2D por prompt: [Ollama](https://ollama.com) con `ollama pull qwen3-vl:8b`

El modo 2D no necesita ningún servicio externo: es OpenCV puro salvo que el prompt pida limpieza con IA.

## Arranque

```powershell
# Terminal 1 — backend (uv instala Python 3.12 y dependencias automáticamente)
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev        # abre http://localhost:5173

# Terminal 3 (solo para modo 3D) — servicio orgánico, tras el setup de organic/README.md
cd organic
uv run uvicorn service:app --port 8001
```

O todo a la vez con `script.bat` desde la raíz.

## Uso

1. Adjunta una foto (📷) — obligatoria en ambos modos — y elige el modo.
2. **🗿 3D (foto)**: para figuras y objetos con volumen. TRELLIS reconstruye la malla; el backend la repara (componente mayor, agujeros, normales) y la apoya en la cama. El tamaño sale del campo "tamaño", o del texto (*"altura 120 mm"*), o de 80 mm por defecto. Exporta STL o 3MF — no hay B-rep ni código.
3. **📐 2D DXF**: para piezas planas (soportes, juntas, plantillas para corte). OpenCV vectoriza el contorno exterior y los agujeros; el resultado se ve como plano 2D en el visor y se exporta como DXF (mm, listo para CAD/láser) o SVG. El texto opcional fija la medida real (*"ancho 60 mm"*) y puede pedir limpieza con IA (*"solo el contorno exterior"*, *"redondea"*) — si qwen3-vl no está disponible o falla, se usa el contorno vectorizado tal cual con un aviso.
4. Cada generación crea una versión nueva en la sesión; los datos viven en `backend/data/sessions/{id}/` y sobreviven reinicios.

> Sesiones antiguas del modo CAD paramétrico (eliminado): sus versiones siguen viéndose y exportando STL/3MF, pero ya no hay export STEP ni "Ver código". Vacía `backend/data/sessions` si quieres empezar de cero.

## Arquitectura

| Componente | Descripción |
|---|---|
| `backend/app/services/sketch.py` | Pipeline 2D: OpenCV (Otsu + contornos RETR_CCOMP + simplificación) → escala en mm → DXF con ezdxf + preview SVG; limpieza opcional con qwen3-vl y fallback al CV puro |
| `backend/app/services/organic.py` | Cliente del servicio orgánico + reparación/normalizado de malla (trimesh) |
| `backend/app/services/dimensions.py` | Extrae la medida real del prompt por regex ("altura 120 mm", "6 cm") |
| `backend/app/services/mesh_service.py` | trimesh: STL→GLB para el visor, watertight, dimensiones, voladizos |
| `backend/app/services/llm.py` | Cliente Ollama (qwen3-vl) para la limpieza 2D; prompt en `app/prompts/sketch_refine.md` |
| `backend/app/routers/` | FastAPI: sesiones, SSE de progreso, export (STL/3MF/DXF/SVG), health |
| `organic/` | Microservicio aparte (uv propio): TRELLIS (o TripoSR) + PyTorch cu128, foto → STL en `:8001` |
| `frontend/` | React: chat con dos modos, visor 3D (react-three-fiber, Z-up) y visor 2D (SVG), export |

## Configuración

Variables de entorno con prefijo `PRINTCAD_` (ver `backend/app/config.py`):

- `PRINTCAD_ORGANIC_SERVICE_URL` (por defecto `http://localhost:8001`), `PRINTCAD_ORGANIC_DEFAULT_SIZE_MM` (80)
- `PRINTCAD_SKETCH_DEFAULT_WIDTH_MM` (100) — ancho asumido si no se indica medida
- `PRINTCAD_SKETCH_MIN_CONTOUR_AREA_FRAC` (0.0005) — filtra motas pequeñas
- `PRINTCAD_SKETCH_SIMPLIFY_EPSILON_FRAC` (0.005) — agresividad de la simplificación de contornos
- `PRINTCAD_MODEL_VISION` (qwen3-vl:8b), `PRINTCAD_OLLAMA_HOST`, `PRINTCAD_BED_SIZE_MM`

## Tests

```powershell
cd backend
uv run pytest        # API, mallas, pipeline 2D completo (sin servicios externos)
```

## Hoja de ruta

- Gizmos de edición manual y panel de parámetros editables.
- Detección de círculos en el modo 2D (agujeros como entidades CIRCLE del DXF en vez de polilíneas).
