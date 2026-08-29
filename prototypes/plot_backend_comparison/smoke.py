"""Dependency/build smoke for the throwaway comparison prototypes."""

from __future__ import annotations

import importlib
import os
import tempfile

from .data import make_demo_data


def main() -> int:
    data = make_demo_data()
    print(f"shared_data curves={len(data)} points={len(data[0].frames)}")
    with tempfile.TemporaryDirectory(prefix="plot-proto-config-") as config:
        os.environ.setdefault("PLOT_PROTO_CONFIG_DIR", config)
        for name in ("silx", "plotpy", "matplotlib"):
            module_name = {
                "silx": "silx_demo",
                "plotpy": "plotpy_demo",
                "matplotlib": "matplotlib_mplcursors",
            }[name]
            try:
                module = importlib.import_module(
                    f"prototypes.plot_backend_comparison.{module_name}"
                )
                if name == "matplotlib":
                    figure, _ = module.build_figure(backend="Agg")
                    print(f"{name}: import/build OK axes={len(figure.axes)}")
                    import matplotlib.pyplot as plt

                    plt.close(figure)
                else:
                    module._require()
                    print(f"{name}: dependency import OK (GUI build not run)")
            except (ImportError, RuntimeError, ModuleNotFoundError) as error:
                print(f"{name}: unavailable — {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
