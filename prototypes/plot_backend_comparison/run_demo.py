"""One-command launcher for the three PROTOTYPE / THROWAWAY demos."""

from __future__ import annotations

import argparse
import importlib
import sys


BACKENDS = {
    "silx": "silx_demo",
    "plotpy": "plotpy_demo",
    "matplotlib": "matplotlib_mplcursors",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PROTOTYPE/THROWAWAY backend comparison (not production code)."
    )
    parser.add_argument("backend", choices=sorted(BACKENDS))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="build without entering a GUI loop (Matplotlib uses Agg)",
    )
    args = parser.parse_args(argv)
    module = importlib.import_module(f"prototypes.plot_backend_comparison.{BACKENDS[args.backend]}")
    try:
        if args.backend == "matplotlib":
            figure, _cursor = module.build_figure(
                args.seed, backend="Agg" if args.smoke else "QtAgg"
            )
            if args.smoke:
                print(f"OK matplotlib: axes={len(figure.axes)} seed={args.seed}")
                figure.canvas.close_event() if hasattr(figure.canvas, "close_event") else None
                return 0
            module.show(args.seed)
        else:
            window, panels = module.build_window(args.seed)
            if args.smoke:
                print(f"OK {args.backend}: panels={len(panels)} seed={args.seed}")
                window.close()
                return 0
            module.show(args.seed)
    except RuntimeError as error:
        print(f"{args.backend}: missing or unusable dependency: {error}", file=sys.stderr)
        return 2
    except ImportError as error:
        print(f"{args.backend}: import failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
