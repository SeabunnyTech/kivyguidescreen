from kivy.graphics import Line, Color, Point, InstructionGroup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.properties import ColorProperty


from time import time

class GridNode:

    def __init__(self, xy, uv):
        self.xy = xy
        self.uv = uv

    def set_index(self, row, column):
        self._row = row
        self._column = column



class MappingGrid:


    def __init__(self, griddata):
        # 載入節點
        self._griddata = griddata
        self._gridsize = griddata['size']
        self._nodes = nodes = [GridNode(xy=xy, uv=uv) for xy, uv in griddata['nodes']]


    def size(self):
        return self._gridsize


    def node(self, row, column):
        # 節點儲存時已經過排序
        w, h = self.size()
        return self._nodes[column + w * row]


    @property
    def griddata(self):
        num_row, num_col = self.size()
        
        nodes = []
        for row in range(num_row):
            for col in range(num_col):
                n = self.node(row, col)
                nodes.append((n.xy, n.uv))

        return dict(size=self.size(), nodes=nodes)


    def size(self):
        return self._gridsize


    def subdivide(self, w, h):
        # add more nodes into the grid
        # meanwhile keep the old nodes' properties
        pass


    @property
    def corners(self):
        return [node.xy for node in self._nodes]


    def closest_node(self, x, y):
        min_distance_square = 100000000
        closest_node = None
        row_count, column_count = self._gridsize
        for c in range(column_count):
            for r in range(row_count):
                nx, ny = self.node(r, c).xy
                distance_square = (x-nx) ** 2 + (y-ny) ** 2
                if distance_square < min_distance_square:
                    min_distance_square = distance_square
                    closest_node = self.node(r, c)

        return closest_node




class GridEditor(Widget):


    line_color = ColorProperty('red')
    blink_color = ColorProperty('yellow')

    def __init__(self, griddata=None, **kw):
        super().__init__(**kw)

        self._mapping_grid = None
        if griddata is not None:
            self.load_grid(griddata=griddata)

        self._is_dragging = False
        self._selected_node = None
        self._blink_time = time()


    def load_grid(self, griddata):
        self._mapping_grid = MappingGrid(griddata=griddata)


    @property
    def griddata(self):
        if self._mapping_grid is None:
            raise RuntimeError("Trying to access griddata before initializing one")

        return self._mapping_grid.griddata


    def update_canvas(self, cursor_position=None):
        if self._mapping_grid is None:
            return

        if cursor_position is None:
            cursor_position = list(Window.mouse_pos)

        self._cursor_position = cursor_position
        #ins = self.homography_instructions
        canvas = self.canvas.after
        canvas.clear()
        canvas.add(Color(*self.line_color))

        # 畫出四條連接線
        p00, pw0, p0h, pwh = [list(p) for p in self._mapping_grid.corners]
        edges = [p00+pw0, pw0+pwh, pwh+p0h, p00+p0h]
        for edge in edges:
            canvas.add(Line(points=edge, width=1))

        if self.disabled:
            return

        # 如果不是正在拖曳中的話就可以即時重選最接近的節點當作 selected_node
        if not self._is_dragging or self._selected_node is None:
            self._selected_node = self._mapping_grid.closest_node(*cursor_position)

        # 畫出選擇線
        selection_line_color = self.blink_color if time() > self._blink_time else self.line_color
        canvas.add(Color(*selection_line_color))
        selected_node = self._selected_node
        canvas.add(Line(points = cursor_position + list(selected_node.xy)))

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

