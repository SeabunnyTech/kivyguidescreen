from kivy.clock import Clock
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, DictProperty, BooleanProperty, ListProperty
from kivyguidescreen import GuideScreen, GuideScreenManager

from kivyguidescreen.widgets.numpyimage import NumpyImage
from kivyguidescreen.widgets.grideditor import GridEditor, Grid

from kivy.uix.label import Label

import numpy as np
import cv2 
from kivy.clock import Clock, mainthread

class TableGuideScreen(GuideScreen):

    switch_monitor_by_digitkey = BooleanProperty(True)


class LocateTableScreen(TableGuideScreen):

    """
    在投影畫面中標出桌面的四角，搭配先前手測的網格以計算桌面尺寸，並以桌面中央為原點，重新上傳手測網格的座標
    """

    table_corners_pixel = StringProperty('table_corners_pixel')
    table_corners_mm = StringProperty('table_corners_mm')
    table_size = ListProperty([])

    def on_enter(self):
        grideditor = self.ids.grideditor
        try:
            table_corners_pixel = self.load_from_manager(self.table_corners_pixel)
            grideditor.load_grid(**table_corners_pixel)
        except KeyError:
            grideditor.init_grid(shape=(2, 2))

        grideditor.disabled = False
        if self.table_size:
            w, h = self.table_size
            self.guide = "用滑鼠靠近選擇頂點，再以滑鼠左鍵拖曳及鍵盤方向鍵調整頂點位置以符合桌面\n\n桌面尺寸 {w} x {h}".format(w=w, h=h)


    def on_press_arrow(self, keyname, dxdy):
        self.ids.grideditor.move_selection(dxdy, scale=0.25)


    def on_leave(self):
        self.ids.grideditor.disabled = True


    def on_press_enter(self):
        grideditor = self.ids.grideditor
        table_corners_pixel = grideditor.griddata
        self.upload_to_manager(**{self.table_corners_pixel : table_corners_pixel})
        if self.table_size:
            w, h = self.table_size
            self.upload_to_manager(**{self.table_corners_mm : Grid(shape=(2,2), pos=[-w/2, -h/2], size=[w, h]).griddata})
        
        self.goto_next_screen()



class VerifyTableScreen(TableGuideScreen):

    '''
    結合手測座標與桌角座標重新輸出手測座標
    以桌角的 P[0,0] P[0,1] 為 x 軸，四角重心為原點計算桌面四角座標
    '''

    projector_grid_mm = StringProperty('StringProperty')
    projector_grid_pixel = StringProperty('projector_grid_pixel')
    table_corners_mm = StringProperty('table_corners_mm')
    table_corners_pixel = StringProperty('table_corners_pixel')
    table_grid_mm = StringProperty('table_grid_mm')
    sensor_areas = DictProperty()

    def on_enter(self):
        from kivyguidescreen.utils.armath import PerspectiveTransform
        # 讀入座標
        projector_grid_mm = self.load_from_manager(self.projector_grid_mm).coords
        projector_grid_pixel = self.load_from_manager(self.projector_grid_pixel).coords
        table_corners_pixel = self.load_from_manager(self.table_corners_pixel).coords

        # 製作從 pixel 到 mm 座標的轉換
        pt = PerspectiveTransform(src_points=projector_grid_pixel, dst_points=projector_grid_mm)

        # 將桌腳的像素座標都轉成 mm 座標
        table_corners_mm = pt.apply(table_corners_pixel)

        # 計算重心與 x 軸
        center = sum(table_corners_mm) / 4
        y_axis_vector = table_corners_mm[2] - table_corners_mm[0]   # 這邊借助了 Grid 的順序 0,0 => 0, 1 => 1, 0
        y_unit = y_axis_vector / np.linalg.norm(y_axis_vector)
        y_unit_complex = y_unit[0] + 1j*y_unit[1]
        x_unit_complex = y_unit_complex / 1j

        # 準備能將座標平移旋轉成桌面座標的函數
        def transform(coords):
            coords = coords - center
            coords_complex = [it[0] + 1j*it[1] for it in coords]
            rotated_coords_complex = [it / x_unit_complex for it in coords_complex]
            return np.array([[it.real, it.imag] for it in rotated_coords_complex]).round(decimals=2)

        # 將桌角座標轉換出來
        self._table_corners_mm = table_corners_mm = transform(table_corners_mm)

        # 將座標顯示在 grideditor 上
        winsize = self.load_from_manager('windowsize')

        if '_labels' not in dir(self):
            self._labels = []
            for idx in range(4):
                label = Label(size_hint=(None, None), size=(0,0), color=[1,1,1])
                self._labels.append(label)
                self.add_widget(label)

        for coord_mm, coord_pixel, label in zip(table_corners_mm, table_corners_pixel, self._labels):
            # 把 label 放在從頂點出發朝中央挪一些的位置
            corner_label_pos = (np.array(coord_pixel) * 0.9 + (np.array(winsize) / 2) * 0.1).tolist()
            label.text = '[ ' + str(coord_mm[0]) + ', ' + str(coord_mm[1]) + ' ]'
            label.pos = corner_label_pos

        self._table_grid_mm = transform(projector_grid_mm)


    def on_press_enter(self):
        # 上傳變數
        self.upload_to_manager(**{self.table_grid_mm : Grid(shape=(2,3), coords=self._table_grid_mm).griddata})
        self.upload_to_manager(**{self.table_corners_mm : Grid(shape=(2,2), coords=self._table_corners_mm).griddata})

        self.goto_next_screen()





class DrawSensorAreaScreen(TableGuideScreen):

    '''
    結合手測座標與桌角座標重新輸出手測座標
    以桌角的 P[0,0] P[0,1] 為 x 軸，四角重心為原點計算桌面四角座標
    '''

    table_corners_mm = StringProperty('table_corners_mm')
    table_corners_pixel = StringProperty('table_corners_pixel')
    sensor_area = DictProperty()

    def on_enter(self):
        from kivyguidescreen.utils.armath import PerspectiveTransform
        # 讀入座標
        table_corners_pixel = self.load_from_manager(self.table_corners_pixel).coords
        table_corners_mm = self.load_from_manager(self.table_corners_mm).coords

        # 將 sensor_area 畫出來
        def pixel_to_table_mm(pixel_coords):
            return PerspectiveTransform(src_points=table_corners_mm, dst_points=table_corners_pixel).apply(pixel_coords)

        canvas = self.canvas.after
        canvas.clear()
        from kivy.utils import QueryDict
        self.sensor_area = QueryDict(self.sensor_area)

        from kivy.graphics import Line, Color
        area = self.sensor_area
        x, y = area.pos
        w, h = area.size
        area_vertices = pixel_to_table_mm([[x, y], [x+w, y], [x+w, y+h], [x, y+h], [x, y]]).reshape(-1).tolist()
        canvas.add(Color(1, 1, 0))
        canvas.add(Line(points=area_vertices))


    def on_press_enter(self):
        self.goto_next_screen()




class TableRefLineScreen(TableGuideScreen):

    vertical_line_x_mm = NumericProperty(0)
    horizontal_line_y_mm = NumericProperty(0)

    table_corners_mm = StringProperty('table_corners_mm')
    table_corners_pixel = StringProperty('table_corners_pixel')

    def on_enter(self):
        from kivyguidescreen.utils.armath import PerspectiveTransform
        # 讀入座標
        table_corners_mm = self.load_from_manager(self.table_corners_mm).coords
        table_corners_pixel = self.load_from_manager(self.table_corners_pixel).coords

        # 建立從 mm 到 pixel 座標的轉換
        pt = PerspectiveTransform(src_points=table_corners_mm, dst_points=table_corners_pixel)

        # 設定兩條參考線的頂點 mm 座標
        r = 20
        max_x = max([it[0] for it in table_corners_mm]) - r
        min_x = min([it[0] for it in table_corners_mm]) + r
        max_y = max([it[1] for it in table_corners_mm]) - r
        min_y = min([it[1] for it in table_corners_mm]) + r

        x = self.vertical_line_x_mm
        y = self.horizontal_line_y_mm

        from kivy.graphics import Line, Color
        self.canvas.after.clear()

        with self.canvas.after:
            Color(1, 1, 0)
            hline_points = pt.apply([min_x, y, max_x, y]).tolist()
            Line(points=hline_points)
            vline_points = pt.apply([x, min_y, x, max_y]).tolist()
            Line(points=vline_points)

    def on_press_enter(self):
        self.goto_next_screen()


from kivy.lang import Builder
Builder.load_string("""

<LocateTableScreen>:

    cursor: 'tiny cross'
    background: 0, 0, .1

    padding: 100
    guide: "挪動四邊形頂點，使它符合桌面邊緣"

    GridEditor:
        id: grideditor


<VerifyTableScreen>:

    cursor: 'hidden'
    background: 0, 0, .1

    guide: "檢查確認桌面四角的座標無誤後，按 enter 進入下一步"


<VerifySensorAreaScreen>:

    cursor: 'hidden'
    background: 0, 0, .1

    guide: "請在感應區塊的角落放上標記後，按 enter 進入下一步"


<TableRefLineScreen>:

    cursor: 'hidden'
    background: 0, 0, .1

    anchor_x: 'right'
    anchor_y: 'top'
    padding: 300
    
    guide: '參考線: x = ' + str(self.vertical_line_x_mm) + ' mm, y = ' + str(self.horizontal_line_y_mm) + ' mm'

""")