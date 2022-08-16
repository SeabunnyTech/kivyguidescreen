class Node:

    def __init__(self, pos, xy):
        self._pos = pos
        self.xy = tuple(xy)

    @property
    def pos(self):
        return self._pos


class Grid:

    def __init__(self, shape=None, coords=None):
        if None not in [shape, coords]:
            self.load(shape=shape, coords=coords)
            return

        if coords is None:
            self.init(shape=shape)
            return

        if shape is None:
            self.load(coords=coords)


    def load(self, coords, shape=None):
        if shape is None:
            shape = [1, len(coords)]

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
        if num_rows < 1 or num_cols < 1:
            raise ValueError("At least 1 rows and 1 columns are expected")

        # 計算每個頂點的水平和垂直間隔
        w, h = size

        row_step = h / (num_rows - 1) if num_rows > 1 else 0
        col_step = w / (num_cols - 1) if num_cols > 1 else 0

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


    def coords(self, dtype=None):
        import numpy as np
        coords = [node.xy for node in self._nodes]
        if dtype in [None, list]:
            return coords
        else:
            return np.array(coords, dtype=dtype)


    @property
    def node_dict(self):
        num_row, num_col = self.shape
        node_dict = {}
        for row in range(num_row):
            for col in range(num_col):
                node_dict[(row, col)] = self.node(row, col).xy
        return node_dict


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



