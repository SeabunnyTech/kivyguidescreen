from kivy.graphics import Line, Color, Point, InstructionGroup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.properties import ColorProperty, ObjectProperty, NumericProperty
from kivy.clock import Clock

from time import time


class Node:

    def __init__(self, pos, xy):
        self._pos = pos
        self.xy = tuple(xy)

    @property
    def pos(self):
        return self._pos


class Grid:

    def __init__(self, shape=None, coords=None, **kw):
        if shape is not None:
            if coords is not None:
                if kw != {}:
                    raise RuntimeError("No parameters are expected when \"coords\" are specified: " + str(**kw) + "")
                self.load(shape, coords)
            else:
                self.init(shape, **kw)


    def load(self, shape, coords):
        num_rows, num_cols = self._shape = shape
        assert num_rows * num_cols == len(coords)

        # 載入節點
        self._nodes = []
        for index, coord in enumerate(coords):
            row, col = index // num_cols, index % num_cols
            node = Node(pos=[row, col], xy=coord)
            self._nodes.append(node)


    def init(self, shape, pos=[0, 0], size=[100, 100]):
        num_rows, num_cols = shape
        if num_rows < 2 or num_cols < 2:
            raise ValueError("At least 2 rows and 2 columns are expected")

        # 計算每個頂點的水平和垂直間隔
        w, h = size
        row_step = h / (num_rows - 1)
        col_step = w / (num_cols - 1)

        # 計算並加入每個節點的座標
        coords = []
        for row in range(num_rows):
            for col in range(num_cols):
                x0, y0 = pos
                coord = (x0 + col_step * col, y0 + row_step * row)
                coords.append(coord)

        self.load(shape, coords)


    @property
    def shape(self):
        return self._shape


    def node(self, row, column):
        # 節點儲存時已經過排序
        num_rows, num_cols = self.shape
        return self._nodes[column + num_cols * row]


    @property
    def griddata(self):
        return dict(shape=self.shape, coords=[node.xy for node in self._nodes])


    def closest_node(self, x, y):
        min_distance_square = 100000000
        closest_node = None
        row_count, column_count = self.shape
        for c in range(column_count):
            for r in range(row_count):
                nx, ny = self.node(r, c).xy
                distance_square = (x-nx) ** 2 + (y-ny) ** 2
                if distance_square < min_distance_square:
                    min_distance_square = distance_square
                    closest_node = self.node(r, c)

        return closest_node




class GridEditor(Widget):

    init_corner_offset = NumericProperty(100)

    # 線條的寬度與顏色
    line_width = NumericProperty(1)
    line_color = ColorProperty('yellow')
    blink_color = ColorProperty('white')

    def __init__(self, shape=None, nodes=None, **kw):
        super().__init__(**kw)

        # 選擇載入 / 新增 或者只產生空的 Grid
        self._grid = None
        if shape is not None:
            if nodes is not None:
                self._load_grid(shape=shape, nodes=nodes)
            else:
                self._init_grid(shape)

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


    def load_grid(self, shape, coords):
        self._grid = Grid(shape=shape, coords=coords)


    @property
    def griddata(self):
        if self._grid is None:
            raise RuntimeError("Trying to access griddata before initializing one")

        return self._grid.griddata


    def selected_node_description(self):
        return str([round(v, 2) for v in self._selected_node.xy])


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

        # 所有的橫格線
        row_num, col_num = grid.shape
        for row in range(row_num):
            for col in range(col_num - 1):
                points = grid.node(row, col).xy + grid.node(row, col+1).xy
                canvas.add(Line(points=points, width=self.line_width))

        # 直格線
        for row in range(row_num - 1):
            for col in range(col_num):
                points = grid.node(row, col).xy + grid.node(row+1, col).xy
                canvas.add(Line(points=points, width=self.line_width))

        if self.disabled:
            return

        # 如果不是正在拖曳中的話就可以即時重選最接近的節點當作 selected_node
        if not self._is_dragging or self._selected_node is None:
            self._selected_node = self._grid.closest_node(*cursor_position)

        # 畫出選擇線
        selection_line_color = self.blink_color if time() > self._blink_time else self.line_color
        canvas.add(Color(*selection_line_color))
        selected_node = self._selected_node
        canvas.add(Line(points = cursor_position + list(selected_node.xy), width=self.line_width))

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


    def move_selection(self, dxdy, blink=True):
        if self._is_dragging:
            return

        dx, dy = dxdy
        x, y = self._selected_node.xy
        self._selected_node.xy = (x+dx, y+dy)

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

