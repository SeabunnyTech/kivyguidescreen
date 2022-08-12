from kivy.clock import Clock
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivyguidescreen import GuideScreen, GuideScreenManager

from kivyguidescreen.widgets.grideditor import GridEditor


class GridEditorScreen(GuideScreen):

    windowsize = StringProperty('windowsize')
    grid_out = StringProperty('griddata')

    def __init__(self, shape=[2,2], **kw):
        super().__init__(**kw)
        self._shape = shape

    def on_enter(self):
        w, h = self.load_from_manager(self.windowsize)

        # 載入先前準備的 griddata 或者初始化一份出來
        grideditor = self.ids.grideditor
        try:
            griddata = self.load_from_manager(self.grid_out)
            grideditor.load_grid(**griddata)
        except KeyError:
            grideditor.init_grid(shape=self._shape)

        grideditor.disabled = False


    def on_leave(self):
        # 沒有 disabled 掉的話它在背景還是會不斷更新外觀
        self.ids.grideditor.disabled = True


    def on_press_arrow(self, keyname, dxdy):
        self.ids.grideditor.move_selection(dxdy)


    def on_press_enter(self):
        griddata = self.ids.grideditor.griddata
        self.upload_to_manager(**{self.grid_out : griddata})
        self.goto_next_screen()


    def undo(self):
        self.goto_previous_screen()



from kivy.lang import Builder
Builder.load_string("""

<GridEditorScreen>:
    background: .2, .2, .4
    cursor: 'tiny cross'

    GridEditor:
        id: grideditor
        disabled: True
        line_color: 1, 1, 0
        blink_color: 1, 1, 1

""")
