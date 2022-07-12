from .grideditor import GridEditor, MappingGrid


class QuadEditor(GridEditor):

    '''
    由 GridEditor 特化而來的僅有四個頂點的 QuadEditor
    '''

    def __init__(self, clockwise_corners=None, **kw):
        if 'griddata' in kw:
            raise ValueError("QuadEditor do not accept arguement 'griddata'. Use 'clockwise_corners' instead")

        super().__init__(**kw)

        if clockwise_corners is not None:
            self.load_quad(clockwise_corners=clockwise_corners)


    def default_corners(self, offset=0):
        of = offset
        w, h = self.size
        return {
            'A' : (of, of),
            'B' : (of, h - of),
            'C' : (w - of, h - of),
            'D' : (w - of, of),
        }


    def selected_node_description(self):
        xy = self._selected_node.xy
        corners = self.clockwise_corners
        id = list(corners.keys())[list(corners.values()).index(xy)]
        return id + ': ' + str([round(v) for v in xy])


    def init_quad(self, corner_offset=0):
        corners = self.default_corners(offset=corner_offset)
        self.load_quad(corners)
        return corners


    def load_quad(self, clockwise_corners):
        A, B, C, D = [clockwise_corners[it] for it in 'ABCD']
        griddata = dict(size=(2, 2), nodes=[A, B, D, C])
        self._mapping_grid = MappingGrid(griddata=griddata)


    def load_grid(self, *args):
        raise AttributeError( "'QuadEditor' object has no attribute 'load_grid'" )


    @property
    def clockwise_corners(self):
        A, B, D, C = self._mapping_grid.griddata['nodes']
        return {it:point for it, point in zip('ABCD', [A, B, C, D])}


    @property
    def griddata(self):
        raise AttributeError( "'QuadEditor' object has no attribute 'load_grid'" )


