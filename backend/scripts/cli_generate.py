"""Headless test harness: prompt -> CadQuery -> STL, no frontend needed.

Usage:
    uv run python scripts/cli_generate.py "a 30x20x10 mm box with a 5 mm hole"
    uv run python scripts/cli_generate.py --image ref.png "washer, 30 mm outer diameter"
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.generation import GenerationFailed, generate_model  # noqa: E402


async def main() -> None:
    args = sys.argv[1:]
    image_bytes = None
    if args and args[0] == "--image":
        image_bytes = Path(args[1]).read_bytes()
        args = args[2:]
    prompt = " ".join(args) or (
        None if image_bytes else "a 30x20x10 mm box with a 5 mm hole through the center"
    )
    out_dir = Path(__file__).resolve().parent.parent / "data" / "cli" / time.strftime("%Y%m%d_%H%M%S")
    print(f"Prompt: {prompt}\nImage: {'yes' if image_bytes else 'no'}\nOutput: {out_dir}\n")

    async def emit(event: str, data: dict) -> None:
        if event == "status":
            print(f"\n[{data['stage']} attempt {data['attempt']}]", flush=True)
        elif event == "vision_result":
            print(f"\nVision brief: {data['brief']}", flush=True)
        elif event == "code_delta":
            print(data["text"], end="", flush=True)

    start = time.time()
    try:
        result = await generate_model(
            request=prompt, image_bytes=image_bytes, out_dir=out_dir, emit=emit
        )
    except GenerationFailed as exc:
        print(f"\n\nFAILED after {exc.attempts} attempts ({time.time() - start:.1f}s)")
        print(f"Last error:\n{exc.last_error}")
        sys.exit(1)

    info = result.mesh_info
    print(f"\n\nOK in {time.time() - start:.1f}s")
    print(f"  dimensions: {info.dimensions_mm['x']} x {info.dimensions_mm['y']} x {info.dimensions_mm['z']} mm")
    print(f"  volume:     {info.volume_mm3} mm^3")
    print(f"  watertight: {info.watertight}")
    for w in info.warnings:
        print(f"  warning:    {w}")
    print(f"  files:      {result.stl_path.name}, {result.step_path.name}, {result.glb_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
