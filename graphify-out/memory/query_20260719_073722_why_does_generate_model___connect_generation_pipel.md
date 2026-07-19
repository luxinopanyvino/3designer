---
type: "query"
date: "2026-07-19T07:37:22.905744+00:00"
question: "Why does generate_model() connect Generation Pipeline & LLM to Job Manager & SSE Events, CAD Executor & Tests, Code Safety Allowlist, Mesh Service & Export?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["generate_model()", "_run_job()", "check_code()", "execute_cad_code()", "analyze_stl()", "LLMService"]
---

# Q: Why does generate_model() connect Generation Pipeline & LLM to Job Manager & SSE Events, CAD Executor & Tests, Code Safety Allowlist, Mesh Service & Export?

## Answer

Expanded from original query via vocab: [generate, model, generation, pipeline, llm, job, manager, sse, executor, safety, allowlist, mesh]. generate_model() (generation.py L54) is the pipeline orchestrator: _run_job() (Job Manager) calls it and it emits SSE progress via JobManager.emit(); it calls LLMService/extract_code (LLM), check_code() (Code Safety AST allowlist), execute_cad_code() (CAD Executor sandbox, indirect), then analyze_stl() and convert_stl_to_glb() (Mesh Service, indirect). It returns GenerationResult or raises GenerationFailed. It bridges 5 communities because it implements the README pipeline LLM -> AST check -> sandbox -> mesh validation end to end.

## Outcome

- Signal: useful

## Source Nodes

- generate_model()
- _run_job()
- check_code()
- execute_cad_code()
- analyze_stl()
- LLMService