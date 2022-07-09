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


    def load_quad(self, clockwise_corners):
        A, B, C, D = clockwise_corners
        griddata = dict(size=(2, 2), nodes=[A, B, D, C])
        self._mapping_grid = MappingGrid(griddata=griddata)


    def load_grid(self, *args):
        raise AttributeError( "'QuadEditor' object has no attribute 'load_grid'" )


    @property
    def clockwise_corners(self):
        A, B, D, C = self._mapping_grid.griddata['nodes']
        return [A, B, C, D]


    @property
    def griddata(self):
        raise AttributeError( "'QuadEditor' object has no attribute 'load_grid'" )


