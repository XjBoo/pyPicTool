"""Optional Qt window controls, kept outside the plot's exported artists."""


def install_toolbar_toggle(figure) -> None:
    """Collapse native Qt navigation without loading Qt on headless backends."""
    canvas = figure.canvas
    manager = getattr(canvas, "manager", None)
    toolbar = getattr(manager, "toolbar", None)
    if toolbar is None or not hasattr(toolbar, "toggleViewAction"):
        return

    from matplotlib.backends.qt_compat import QtCore, QtWidgets

    if not isinstance(toolbar, QtWidgets.QToolBar):
        return

    class ToolbarToggle(QtWidgets.QToolButton):
        def __init__(self):
            super().__init__(canvas)
            self.setObjectName("plotToolbarToggle")
            self.setText("工具栏")
            self.setToolTip("展开 / 收起导航工具栏")
            self.setAccessibleName("展开或收起工具栏")
            self.setCheckable(True)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setAutoRaise(True)
            self.setStyleSheet(
                "QToolButton { color: #64748B; background: #F3F5F7; "
                "border: 1px solid #CCD5DF; border-radius: 3px; padding: 2px 6px; }"
                "QToolButton:checked, QToolButton:hover { background: #E5EAF0; }"
            )
            self.adjustSize()
            self.toggled.connect(self.toggle_toolbar)
            toolbar.toggleViewAction().toggled.connect(self.setChecked)
            canvas.installEventFilter(self)
            self.reposition()
            self.show()

        def reposition(self):
            self.move(max(0, canvas.width() - self.width() - 8), 4)
            self.raise_()

        def eventFilter(self, watched, event):
            if watched is canvas and event.type() == QtCore.QEvent.Type.Resize:
                self.reposition()
            return super().eventFilter(watched, event)

        def toggle_toolbar(self, visible):
            if not visible:
                # Hiding controls must not leave an invisible navigation lock.
                if toolbar.mode.name == "PAN":
                    toolbar.pan()
                elif toolbar.mode.name == "ZOOM":
                    toolbar.zoom()
            toolbar.setVisible(visible)
            canvas.setFocus()

    toolbar.hide()
    # Qt parent ownership retains the control for the canvas lifetime.
    ToolbarToggle()
