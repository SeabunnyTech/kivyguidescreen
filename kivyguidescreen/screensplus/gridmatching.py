from kivy.clock import Clock
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, DictProperty
from kivyguidescreen import GuideScreen, GuideScreenManager

from kivyguidescreen.widgets.numpyimage import NumpyImage
from kivyguidescreen.widgets.grideditor import GridEditor, Grid

import numpy as np

from kivy.clock import Clock, mainthread


from kivyguidescreen.utils.recursive import recursive_round


class GridMatchingScreen(GuideScreen):

    """
    將相機影像與桌面座標配對 / 算出感測範圍內的上視圖
    """

    row_shift = NumericProperty(0)
    column_shift = NumericProperty(0)

    sioevent = StringProperty("")
    grid_src = StringProperty('grid_src')
    grid_dst = StringProperty('grid_dst')
    grid_mapping_out = StringProperty('quad_mapping')


    def load_pairs(self):
        # 讀入兩組 grid 的頂點座標
        grid_src = self.load_from_manager(self.grid_src)
        grid_dst = self.load_from_manager(self.grid_dst)
        src_dict = Grid(**grid_src).node_dict
        dst_dict = Grid(**grid_dst).node_dict

        # 將指定頂點加上 row_shift 及 col_shift 後湊對
        grid_mapping = []
        d_row, d_col = self.row_shift, self.column_shift
        for row_col, src_coord in src_dict.items():
            row, col = row_col
            dst_coord = dst_dict[(row + d_row, col + d_col)]
            rounded_coords = recursive_round([src_coord, dst_coord])
            grid_mapping.append(rounded_coords)

        return grid_mapping


    def on_press_space(self):
        # 將配對傳送至 server 向指定節點 set_config
        self._grid_mapping = self.load_pairs()
        self.socketio_client.emit(
            event='set_config',
            data=dict(path=self.sioevent.lower(), config={'point_pairs' : self._grid_mapping}),
            namespace=None,
            callback=self._done_setting_callback)


    def _done_setting_callback(self, *ars):
        self.guide = self.format_id('已將 {grid_src} 到 {grid_dst} 的座標對應傳送至 {sioevent}\n\n') + str(self._grid_mapping)
        self.upload_to_manager(**{self.grid_mapping_out : self._grid_mapping})


    def format_id(self, string):
        return string.format(grid_src=self.grid_src, grid_dst=self.grid_dst, sioevent=self.sioevent)


    def on_press_enter(self):
        self.goto_next_screen()



from kivy.lang import Builder
Builder.load_string("""

<GridMatchingScreen>:

    cursor: 'hidden'
    background: 0, 0, .1

    guide: self.format_id("按下空白鍵以將  {grid_src}  到  {grid_dst}  的座標對應傳送至 {sioevent}")

""")