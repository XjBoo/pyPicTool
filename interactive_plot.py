import numpy as np
import matplotlib.pyplot as plt

class DataCursor:
    """
    自定义游标类（支持多数据系列）：
    1. 鼠标悬停自动吸附到最近数据点（跨所有系列，基于屏幕像素的欧氏距离）。
    2. 所有未锁定的游标同步移动到同一帧位置，方便对比不同系列的数据。
    3. 支持方向键及 Home/End 键精确移动游标。
    4. 每个系列有一个默认游标，Shift+左键可新增锁定游标。
    """
    active = None  # 当前"激活"的游标实例（用于键盘事件只作用于一个子图）

    class Cursor:
        """单个游标实例（竖线 + 高亮点 + tooltip）。"""

        def __init__(self, ax, x0, y0, series_idx, color='red'):
            self.ax = ax
            self.series_idx = series_idx  # 所属系列索引
            self.current_index = 0
            self.locked = False  # 普通左键切换锁定/解锁

            self.vline, = ax.plot([x0, x0], [y0, y0], 'k--', alpha=0.5, zorder=4)
            self.highlight, = ax.plot([x0], [y0], marker='o', color=color,
                                      markersize=8, zorder=5)
            self.tooltip = ax.annotate(
                "",
                xy=(0, 0),
                xytext=(20, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.8),
                arrowprops=dict(arrowstyle="->"),
                visible=False,
            )
            self.tooltip.draggable(True)

    def __init__(self, ax, series_list):
        """
        ax: matplotlib 坐标轴
        series_list: 列表，每个元素为 dict，包含:
            - 'frames': array-like, X 轴数据
            - 'values': array-like, Y 轴数据
            - 'label': str, 数据系列名称（用于 tooltip 显示）
            - 'color': str, 系列颜色（用于游标高亮点）
        所有系列应共享相同的 frames（X 轴数据），以便游标同步移动。
        """
        self.ax = ax
        self.series_list = series_list
        # 确保 frames/values 为 numpy 数组
        for s in self.series_list:
            s['frames'] = np.asarray(s['frames'])
            s['values'] = np.asarray(s['values'])
        self._disp_xy_list = None  # 每个系列的屏幕坐标缓存 list of (N,2) arrays
        self._last_mouse_px = None  # (x_px, y_px) 最近一次鼠标位置（屏幕像素）
        self._selected = None  # 当前被选择（hover/键盘生效）的 Cursor
        self.cursors = []

        # 为每个系列初始化一个默认游标：未锁定（随鼠标移动）
        for s_idx, series in enumerate(self.series_list):
            x0, y0 = series['frames'][0], series['values'][0]
            color = series.get('color', 'red')
            c = DataCursor.Cursor(ax, x0, y0, s_idx, color)
            self.cursors.append(c)

        self._selected = self.cursors[0]  # 默认选中第一个系列的游标

        self.fig = ax.figure
        # 绑定事件
        self.cid_motion = self.fig.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.cid_key = self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        self.cid_click = self.fig.canvas.mpl_connect('button_press_event', self.on_click)

        # 当坐标轴范围/画布重绘变化时，刷新数据点的屏幕坐标缓存
        self.cid_draw = self.fig.canvas.mpl_connect('draw_event', self._refresh_disp_cache)
        self.ax.callbacks.connect('xlim_changed', self._refresh_disp_cache)
        self.ax.callbacks.connect('ylim_changed', self._refresh_disp_cache)

        self._refresh_disp_cache()
        # 初始化所有游标到第一个数据点
        for c in self.cursors:
            self._update_cursor_visuals(c, 0)

    def _refresh_disp_cache(self, _event=None):
        """刷新所有系列的屏幕坐标缓存。"""
        self._disp_xy_list = []
        for series in self.series_list:
            xy = np.column_stack([series['frames'], series['values']])
            self._disp_xy_list.append(self.ax.transData.transform(xy))

    def _nearest_point_from_px(self, x_px, y_px):
        """
        在所有系列中查找离屏幕像素 (x_px, y_px) 最近的数据点。
        返回 (series_idx, local_idx)。
        """
        if self._disp_xy_list is None:
            self._refresh_disp_cache()
        best_d2 = None
        best_s_idx = None
        best_local_idx = None
        for s_idx, disp_xy in enumerate(self._disp_xy_list):
            dx = disp_xy[:, 0] - x_px
            dy = disp_xy[:, 1] - y_px
            d2_arr = dx * dx + dy * dy
            min_idx = int(np.argmin(d2_arr))
            min_d2 = d2_arr[min_idx]
            if best_d2 is None or min_d2 < best_d2:
                best_d2 = min_d2
                best_s_idx = s_idx
                best_local_idx = min_idx
        return best_s_idx, best_local_idx

    def _cursor_point_px(self, cursor):
        """获取游标当前指向的数据点在屏幕像素中的坐标。"""
        if self._disp_xy_list is None:
            self._refresh_disp_cache()
        return self._disp_xy_list[cursor.series_idx][cursor.current_index]

    def _select_nearest_cursor_to_mouse(self):
        """选择离鼠标最近的游标（考虑游标当前指向的点与鼠标的距离）。"""
        if self._last_mouse_px is None or not self.cursors:
            return self._selected
        mx, my = self._last_mouse_px
        best = None
        best_d2 = None
        for c in self.cursors:
            px, py = self._cursor_point_px(c)
            d2 = (px - mx) ** 2 + (py - my) ** 2
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best = c
        if best is not None:
            self._selected = best
        return self._selected

    def _update_cursor_visuals(self, cursor, local_idx):
        """更新游标的图形元素（竖线、高亮点、tooltip）到指定位置。"""
        series = self.series_list[cursor.series_idx]
        frames = series['frames']
        values = series['values']

        if not (0 <= local_idx < len(frames)):
            return

        cursor.current_index = local_idx
        x, y = frames[local_idx], values[local_idx]

        # 获取当前 Y 轴范围以保持竖线高度
        y_min, y_max = self.ax.get_ylim()

        # 更新图形数据
        cursor.vline.set_data([x, x], [y_min, y_max])
        cursor.highlight.set_data([x], [y])
        cursor.tooltip.xy = (x, y)
        label = series.get('label', f'Series {cursor.series_idx}')
        cursor.tooltip.set_text(f"{label}\nFrame: {int(x)}\nValue: {y:.4f}")
        cursor.tooltip.set_visible(True)

    def on_hover(self, event):
        # 检查鼠标是否在坐标系内
        if event.inaxes != self.ax:
            if DataCursor.active is self:
                DataCursor.active = None
            return

        # 确保同时获取到屏幕坐标
        if event.x is None or event.y is None:
            return

        DataCursor.active = self
        self._last_mouse_px = (event.x, event.y)

        # 在所有系列中找到离鼠标最近的数据点
        s_idx, local_idx = self._nearest_point_from_px(event.x, event.y)

        # 选择离鼠标最近的游标（用于后续点击/键盘操作）
        self._select_nearest_cursor_to_mouse()

        # 所有未锁定的游标同步移动到 local_idx（同一帧位置）
        need_draw = False
        for cursor in self.cursors:
            if not cursor.locked and cursor.current_index != local_idx:
                self._update_cursor_visuals(cursor, local_idx)
                need_draw = True

        if need_draw:
            self.fig.canvas.draw_idle()

    def on_click(self, event):
        # 只处理当前子图内的左键点击
        if event.inaxes != self.ax:
            return
        if getattr(event, "button", None) != 1:
            return

        DataCursor.active = self
        if event.x is not None and event.y is not None:
            self._last_mouse_px = (event.x, event.y)

        # 点击在任意 tooltip 上时交给拖拽逻辑，避免误触发
        for c in self.cursors:
            contains, _ = c.tooltip.contains(event)
            if contains:
                self._selected = c
                return

        is_shift = "shift" in str(getattr(event, "key", "")).lower()

        # Shift + 左键：新增一个游标点（默认锁定）
        if is_shift:
            if event.x is None or event.y is None:
                return
            s_idx, local_idx = self._nearest_point_from_px(event.x, event.y)
            series = self.series_list[s_idx]
            x, y = series['frames'][local_idx], series['values'][local_idx]
            color = series.get('color', 'red')
            c = DataCursor.Cursor(self.ax, x, y, s_idx, color)
            c.locked = True
            self.cursors.append(c)
            self._selected = c
            self._update_cursor_visuals(c, local_idx)
            self.fig.canvas.draw_idle()
            return

        # 普通左键：对"离鼠标最近的游标点"切换锁定/解锁
        cursor = self._select_nearest_cursor_to_mouse()
        if cursor is None:
            return
        cursor.locked = not cursor.locked

        # 刚锁定时，将该游标先吸附到点击位置的最近点
        if cursor.locked:
            if event.x is None or event.y is None:
                return
            s_idx, local_idx = self._nearest_point_from_px(event.x, event.y)
            # 锁定游标可能需要切换到点击所在的系列
            if cursor.series_idx != s_idx:
                cursor.series_idx = s_idx
                color = self.series_list[s_idx].get('color', 'red')
                cursor.highlight.set_color(color)
            self._update_cursor_visuals(cursor, local_idx)
            self.fig.canvas.draw_idle()
        else:
            # 解锁时保持当前点，但允许后续 hover 更新
            self.fig.canvas.draw_idle()

    def on_key(self, event):
        # 只响应"激活"的子图，避免 6 个子图同时移动
        if DataCursor.active is not self:
            return
        cursor = self._select_nearest_cursor_to_mouse()
        if cursor is None:
            return

        # 获取按键并统一转为小写
        key = getattr(event, 'key', '').lower()

        # 方向键只在当前游标所属系列内移动
        frames = self.series_list[cursor.series_idx]['frames']

        if key == 'right':
            new_idx = cursor.current_index + 1
        elif key == 'left':
            new_idx = cursor.current_index - 1
        elif key == 'home':
            new_idx = 0
        elif key == 'end':
            new_idx = len(frames) - 1
        else:
            return  # 忽略非导航键

        if 0 <= new_idx < len(frames):
            self._update_cursor_visuals(cursor, new_idx)
            self.fig.canvas.draw_idle()

def main():
    # 1. 共享的时间轴数据
    frames = np.arange(100)

    # 2. 创建 3 行 2 列的子图布局 (共 6 张子图)
    fig, axes = plt.subplots(3, 2, figsize=(12, 10))
    axes = axes.flatten()

    # 用于存储所有 DataCursor 实例，防止被垃圾回收导致交互失效
    cursors = []

    # 3. 循环生成数据并配置每个子图
    for i, ax in enumerate(axes):
        # 模拟 6 组不同的数据 (例如不同频率的信号)
        freq = 0.05 * (i + 1)
        values = np.sin(frames * freq) + np.random.normal(0, 0.1, 100)
        # 第二组数据（蓝色点）
        freq2 = 0.03 * (i + 1)
        values2 = np.cos(frames * freq2) + np.random.normal(0, 0.15, 100)

        # 绘制基础图形
        ax.plot(frames, values, label=f'Signal {i+1}', zorder=1)
        ax.scatter(frames, values, c='red', s=15, zorder=2, alpha=0.6)
        ax.plot(frames, values2, color='blue', alpha=0.5, zorder=1,
                label=f'Signal {i+1} (blue)')
        ax.scatter(frames, values2, c='blue', s=15, zorder=2, alpha=0.6)

        # 为每个子图激活独立的游标，传入两组数据系列
        series_list = [
            {'frames': frames, 'values': values,
             'label': f'Signal {i+1} (red)', 'color': 'red'},
            {'frames': frames, 'values': values2,
             'label': f'Signal {i+1} (blue)', 'color': 'blue'},
        ]
        cursor = DataCursor(ax, series_list)
        cursors.append(cursor)

        # 样式设置
        ax.set_title(f"Interactive Plot {i+1}")
        ax.set_xlabel("Frame Number")
        ax.set_ylabel("Value")
        ax.legend(loc='upper right')
        ax.grid(True, linestyle='--', alpha=0.6)

    # 自动调整子图间距
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()