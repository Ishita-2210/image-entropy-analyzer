"""python -m backend.app.cli image.png [more images] --mode preview --output result.json"""

import argparse
import json
import sys
from pathlib import Path

from backend.app.core.config import Settings
from backend.app.schemas.models import AnalysisOptions
from backend.app.services.analysis import analyse
from backend.app.services.images import ImageStore


def main():
    parser = argparse.ArgumentParser(description="Image Entropy Analyzer: shared scientific engine")
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--mode", choices=["exact", "preview"], default="exact")
    parser.add_argument("--alpha", type=float, default=2)
    parser.add_argument("--levels", type=int, default=16)
    parser.add_argument("--window", type=int, default=9)
    parser.add_argument("--frame", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
        store = ImageStore(settings)
        options = AnalysisOptions(
            mode=args.mode, alpha=args.alpha, levels=args.levels, window=args.window
        )
        results = []
        for path in args.images:
            if path.stat().st_size > settings.max_upload_mb * 1024**2:
                raise ValueError("Image exceeds upload limit.")
            info = store.add(path.read_bytes(), path.name, args.frame)
            results.append(analyse(store.get(info.id), settings, options))
        text = json.dumps(results[0] if len(results) == 1 else results, indent=2, allow_nan=False)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
