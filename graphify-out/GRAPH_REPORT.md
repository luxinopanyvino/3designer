# Graph Report - C:/project/3d_print  (2026-07-19)

## Corpus Check
- Corpus is ~14,380 words - fits in a single context window. You may not need a graph.

## Summary
- 396 nodes · 579 edges · 37 communities (30 shown, 7 thin omitted)
- Extraction: 84% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 89 edges (avg confidence: 0.78)
- Token cost: 173,344 input · 0 output

## Community Hubs (Navigation)
- Frontend API Client & Types
- Job Manager & SSE Events
- Backend API Tests
- Frontend Dependencies
- Backend Config & Routers
- Generation Pipeline & LLM
- LLM Prompts & Organic Docs
- Mesh Service & Export
- Session Store
- TSConfig App
- TSConfig Node
- CAD Executor & Tests
- Code Safety Allowlist
- xformers SDPA Shim
- Organic Microservice
- Social Icons Sprite
- Sandbox Runner
- 3D Viewer Components
- Oxlint Config
- Favicon Branding
- torchmcubes Shim
- Hero Illustration
- React Logo Asset
- TSConfig Root
- Kaolin Testing Shim
- Frontend HTML Entry
- Kaolin Package Shim
- xformers Package Shim
- Backend Package Meta
- Organic Package Meta

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 18 edges
2. `generate_model()` - 15 edges
3. `useAppStore` - 15 edges
4. `compilerOptions` - 15 edges
5. `SessionStore` - 14 edges
6. `Session` - 13 edges
7. `execute_cad_code()` - 12 edges
8. `check_code()` - 10 edges
9. `analyze_stl()` - 10 edges
10. `MeshInfo` - 9 edges

## Surprising Connections (you probably didn't know these)
- `TRELLIS (Microsoft, default organic engine)` --semantically_similar_to--> `TRELLIS engine (image-large, default)`  [INFERRED] [semantically similar]
  README.md → organic/README.md
- `TripoSR (legacy organic engine)` --semantically_similar_to--> `TripoSR engine (legacy, faster but less detailed)`  [INFERRED] [semantically similar]
  README.md → organic/README.md
- `Refine prompt template` --implements--> `Prompt to CadQuery generation pipeline (LLM -> AST check -> sandbox -> mesh validation)`  [INFERRED]
  backend/app/prompts/refine.md → README.md
- `health()` --calls--> `organic_service_healthy()`  [INFERRED]
  backend/app/routers/health.py → backend/app/services/organic.py
- `box_stl()` --calls--> `execute_cad_code()`  [INFERRED]
  backend/tests/test_mesh_service.py → backend/app/services/cad_executor.py

## Import Cycles
- 1-file cycle: `organic/xformers/ops/__init__.py -> organic/xformers/ops/__init__.py`

## Hyperedges (group relationships)
- **LLM prompt suite for CadQuery generation (system + generate + refine + repair + vision)** — backend_app_prompts_system_cadquery_system_prompt, backend_app_prompts_generate_template, backend_app_prompts_refine_template, backend_app_prompts_repair_template, backend_app_prompts_vision_analyze_prompt [EXTRACTED 1.00]
- **Organic photo-to-mesh flow (mode + engines + shims + VRAM lock)** — readme_organic_mode, organic_readme_organic_service, organic_readme_trellis_engine, organic_readme_triposr_engine, organic_readme_windows_shims, organic_readme_vram_lock [EXTRACTED 1.00]

## Communities (37 total, 7 thin omitted)

### Community 0 - "Frontend API Client & Types"
Cohesion: 0.12
Nodes (28): createSession(), exportUrl(), getCode(), getHealth(), getSession(), postMessage(), request(), subscribeEvents() (+20 more)

### Community 1 - "Job Manager & SSE Events"
Cohesion: 0.10
Nodes (21): version_urls(), _run_job(), _run_organic_job(), Job, JobManager, In-memory generation jobs with replayable event logs for SSE.  Events are append, Async generator of sse-starlette event dicts; ends after a terminal event., generate_organic_model() (+13 more)

### Community 2 - "Backend API Tests"
Cohesion: 0.10
Nodes (17): extract_json(), Pull a JSON object out of an LLM reply (fenced or bare); None if unparseable., client(), fake_generation(), Replace the LLM+CAD pipeline with a stub that writes real (tiny) files., _sse_events(), test_generation_failure_reported(), test_session_lifecycle() (+9 more)

### Community 3 - "Frontend Dependencies"
Cohesion: 0.07
Nodes (27): Vite (frontend build tool), dependencies, react, react-dom, @react-three/drei, @react-three/fiber, three, zustand (+19 more)

### Community 4 - "Backend Config & Routers"
Cohesion: 0.13
Nodes (21): Settings, Process-wide singletons shared by the routers., health(), create_session(), get_code(), get_model_glb(), get_session(), _get_session_or_404() (+13 more)

### Community 5 - "Generation Pipeline & LLM"
Cohesion: 0.10
Nodes (20): generate_model(), GenerationFailed, GenerationResult, Exception, Path, Orchestrator: LLM -> safety check -> sandboxed execution -> mesh validation, wit, First generation: pass `request`. Refinement: pass `previous_code` + `instructio, extract_code() (+12 more)

### Community 6 - "LLM Prompts & Organic Docs"
Cohesion: 0.11
Nodes (25): Generate prompt template, Refine prompt template, Repair prompt template, CadQuery cheat sheet (API calls covering most functional parts), Few-shot examples (bracket, hub, L-bracket, box), Fillet/chamfer rules (decorative, omit when in doubt), Strict output rules (one python block, result var, mm, UPPER_CASE params, z>=0), CadQuery system prompt (rules + cheat sheet + few-shots) (+17 more)

### Community 7 - "Mesh Service & Export"
Cohesion: 0.13
Nodes (21): export_model(), analyze_stl(), convert_stl_to_3mf(), convert_stl_to_glb(), DegenerateMeshError, _overhang_fraction(), Exception, Path (+13 more)

### Community 8 - "Session Store"
Cohesion: 0.21
Nodes (8): MeshInfo, Message, Path, Per-session state: message history + immutable model versions.  In-memory dict f, Session, SessionStore, Version, Lock

### Community 9 - "TSConfig App"
Cohesion: 0.10
Nodes (19): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+11 more)

### Community 10 - "TSConfig Node"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 11 - "CAD Executor & Tests"
Cohesion: 0.23
Nodes (11): ExecResult, execute_cad_code(), _parse_runner_output(), Path, Runs LLM-generated CadQuery code in an isolated subprocess with a timeout., The runner prints one JSON line; generated code may print noise before it., test_infinite_loop_times_out(), test_missing_result_variable() (+3 more)

### Community 12 - "Code Safety Allowlist"
Cohesion: 0.26
Nodes (10): check_code(), Static AST allowlist check for LLM-generated CadQuery code.  This runs in-proces, Return a human/LLM-readable error message if the code is unsafe, else None., test_forbidden_dunder(), test_forbidden_import(), test_forbidden_import_from(), test_forbidden_name(), test_numpy_and_math_allowed() (+2 more)

### Community 13 - "xformers SDPA Shim"
Cohesion: 0.25
Nodes (7): BlockDiagonalMask, Minimal BlockDiagonalMask: only records the per-sample sequence lengths; `ops.m, memory_efficient_attention(), Tensor, SDPA-backed implementation of the xformers ops TRELLIS uses.  TRELLIS (trellis, _sdpa(), unbind()

### Community 14 - "Organic Microservice"
Cohesion: 0.31
Nodes (8): generate(), _generate_sync(), _generate_trellis(), _generate_triposr(), _get_trellis(), _get_triposr(), UploadFile, PrintCAD organic microservice: photo -> neural 3D mesh.  Runs as a separate pr

### Community 15 - "Social Icons Sprite"
Cohesion: 0.43
Nodes (8): Bluesky Icon (symbol #bluesky-icon), Discord Icon (symbol #discord-icon), Documentation Icon (symbol #documentation-icon), GitHub Icon (symbol #github-icon), Social/Community Icon (symbol #social-icon), Social / Community Links UI Concept, Icon Sprite Sheet (icons.svg), X (Twitter) Icon (symbol #x-icon)

### Community 16 - "Sandbox Runner"
Cohesion: 0.48
Nodes (6): emit(), fail(), main(), Standalone sandbox runner, executed in a subprocess by cad_executor.  Usage: pyt, trimmed_traceback(), BaseException

### Community 17 - "3D Viewer Components"
Cohesion: 0.33
Nodes (3): MATERIAL, ModelMesh(), Viewer()

### Community 18 - "Oxlint Config"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 19 - "Favicon Branding"
Cohesion: 0.67
Nodes (4): PrintCAD Favicon (Lightning Bolt Icon), Lightning Bolt Motif, PrintCAD App Branding, Purple Gradient Blur Style (display-p3 palette)

### Community 20 - "torchmcubes Shim"
Cohesion: 0.50
Nodes (3): marching_cubes(), Tensor, Drop-in replacement for the `torchmcubes` package used by TripoSR.  The real tor

### Community 21 - "Hero Illustration"
Cohesion: 0.67
Nodes (3): App.css .hero section style, Hero Illustration (stacked slab graphic), 3D Print Layer / Extrusion Motif

### Community 22 - "React Logo Asset"
Cohesion: 0.67
Nodes (3): React Logo (SVG asset), React Framework, Vite React Template Default Asset

## Ambiguous Edges - Review These
- `Lightning Bolt Motif` → `PrintCAD App Branding`  [AMBIGUOUS]
  frontend/public/favicon.svg · relation: conceptually_related_to
- `Hero Illustration (stacked slab graphic)` → `App.css .hero section style`  [AMBIGUOUS]
  frontend/src/assets/hero.png · relation: references

## Knowledge Gaps
- **75 isolated node(s):** `printcad-backend`, `$schema`, `plugins`, `react/rules-of-hooks`, `react/only-export-components` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Lightning Bolt Motif` and `PrintCAD App Branding`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Hero Illustration (stacked slab graphic)` and `App.css .hero section style`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `SessionStore` connect `Session Store` to `Backend API Tests`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `generate_model()` connect `Generation Pipeline & LLM` to `Job Manager & SSE Events`, `CAD Executor & Tests`, `Code Safety Allowlist`, `Mesh Service & Export`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `client()` connect `Backend API Tests` to `Session Store`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `generate_model()` (e.g. with `_run_job()` and `execute_cad_code()`) actually correct?**
  _`generate_model()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `SessionStore` (e.g. with `MeshInfo` and `client()`) actually correct?**
  _`SessionStore` has 2 INFERRED edges - model-reasoned connections that need verification._