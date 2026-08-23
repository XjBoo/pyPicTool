# Interactive plotting

The project now separates three concerns:

- `interactive_plotting.model` defines `SeriesData`, a temporary internal
  plotting format at the future adapter boundary. It is not a contract for the
  external data-producing script, whose data format is still unknown.
- `interactive_plotting.core` owns reusable Matplotlib construction,
  `PlotSession`, and the existing cursor interaction implementation.
- `interactive_plotting.demo` owns artificial data, the six-panel demo layout,
  and the only blocking `plt.show()` call.

Reusable callers construct internal series and retain the returned session:

```python
from interactive_plotting import SeriesData, create_interactive_plot

series = [SeriesData(frames=[0, 1], values=[0.0, 1.0], label="example")]
session = create_interactive_plot(series)
session.figure.show()
```

Callers can later close the figure with their normal Matplotlib lifecycle,
such as `matplotlib.pyplot.close(session.figure)`. A future adapter should map
the real producer's data into `SeriesData`; no business-specific adapter is
defined yet.

For manual testing in VS Code, run `interactive_plot.py` directly.
