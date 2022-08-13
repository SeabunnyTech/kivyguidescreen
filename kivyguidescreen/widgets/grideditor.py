from kivy.graphics import Line, Color, Point, InstructionGroup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.properties import ColorProperty, ObjectProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock

from time import time

from ..utils.grid import Grid



class GridEditor(Widget):

    init_corner_offset = NumericProperty(100)

    # 線條的寬度與顏色
    draw_line = BooleanProperty(True)
    line_width = NumericProperty(1)
    line_color = ColorProperty('yellow')
    blink_color = ColorProperty('white')

    # 節點的標示
    draw_nodes = BooleanProperty(False)
    cross_diameter = NumericProperty(80)

    def __init__(self, shape=None, coords=None, **kw):
        super().__init__(**kw)

        # 選擇載入 / 新增 或者只產生空的 Grid
        self._grid = None
        if shape is not None:
            if coords is not None:
                self.load_grid(shape=shape, coords=coords)
            else:
                self.init_grid(shape)

        self._is_dragging = False
        self._selected_node = None
        self._blink_time = time()

        self._render_routine = None if self.disabled else Clock.schedule_interval(self.update_canvas, 1/60)


    def on_disabled(self, *args):
        if self.disabled:
            if not self._render_routine:
                return
            self._render_routine.cancel()
            self.update_canvas()
            self._render_routine = None
        else:
            if self._render_routine is None:
                self._render_routine = Clock.schedule_interval(self.update_canvas, 1/60)


    def init_grid(self, shape=[2,2]):
        of = self.init_corner_offset
        w, h = self.size
        self._grid = Grid(shape=shape, pos=[of, of], size=[w-2*of, h-2*of])


    def load_grid(self, coords, shape=None):
        self._grid = Grid(shape=shape, coords=coords)


    @property
    def griddata(self):
        if self._grid is None:
            raise RuntimeError("Trying to access griddata before initializing one")

        return self._grid.griddata


    def selected_node_description(self):
        node = self._selected_node
        return 'P{pos}: '.format(pos=node.pos) + str(tuple([round(v, 2) for v in node.xy]))


    def update_canvas(self, *dt):
        grid = self._grid
        if grid is None:
            return

        cursor_position = list(self.to_widget(*Window.mouse_pos))

        self._cursor_position = cursor_position
        #ins = self.homography_instructions
        canvas = self.canvas.after
        canvas.clear()
        canvas.add(Color(*self.line_color))

        def line(points):
            canvas.add(Line(points=points, width=self.line_width))

        if self.draw_line:

            # 所有的橫格線
            row_num, col_num = grid.shape
            for row in range(row_num):
                for col in range(col_num - 1):
                    points = grid.node(row, col).xy + grid.node(row, col+1).xy
                    line(points)

            # 直格線
            for row in range(row_num - 1):
                for col in range(col_num):
                    points = grid.node(row, col).xy + grid.node(row+1, col).xy
                    line(points)

        if self.draw_nodes:
            r = self.cross_diameter / 2
            for point in grid.coords():
                u,v = point
                line(points=[u-r, v, u+r, v])
                line(points=[u, v-r, u, v+r])

        if self.disabled:
            return

        # 如果不是正在拖曳中的話就可以即時重選最接近的節點當作 selected_node
        if not self._is_dragging or self._selected_node is None:
            self._selected_node = self._grid.closest_node(*cursor_position)

        # 畫出選擇線
        selection_line_color = self.blink_color if time() > self._blink_time else self.line_color
        canvas.add(Color(*selection_line_color))
        selected_node = self._selected_node
        line(points = cursor_position + list(selected_node.xy))

        # 顯示頂點的座標以及代號
        label = self.ids.coord_label
        label.pos = cursor_position
        label.text = self.selected_node_description()

        # dragging 狀態下要移動頂點
        if self._is_dragging:
            mx, my = cursor_position
            sx, sy = self.drag_start_mouse_pos
            cx, cy = self.drag_start_corner_pos

            selected_node.xy = (cx+mx-sx, cy+my-sy)


    def on_touch_down(self, touch):
        self._is_dragging = True
        self.drag_start_mouse_pos = touch.pos
        self.drag_start_corner_pos = self._selected_node.xy


    def on_touch_up(self, touch):
        self._is_dragging = False


    def move_selection(self, dxdy, scale=1.0, blink=True):
        if self._is_dragging:
            return

        dx, dy = dxdy
        x, y = self._selected_node.xy
        self._selected_node.xy = (x + dx * scale, y + dy * scale)

        # 產生 blink 變色效果
        if blink:
            self._blink_time = time() + 0.1



from kivy.lang import Builder
Builder.load_string("""

<GridEditor>:
    Label:
        id: coord_label
        size_hint: None, None
        size: self.texture_size
        color: root.blink_color
""")

