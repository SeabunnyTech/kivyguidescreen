from kivy.clock import Clock
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, ListProperty, DictProperty
from kivyguidescreen import GuideScreen, GuideScreenManager

from kivyguidescreen.widgets.numpyimage import NumpyImage
from kivyguidescreen.widgets.grideditor import GridEditor, Grid

import numpy as np
import cv2

from kivy.clock import Clock, mainthread

from kivyguidescreen.utils.armath import PerspectiveTransform, find_homography

from kivyguidescreen.utils.recursive import recursive_round



class CameraQuadScreen(GuideScreen):

    """
    先在畫面中顯示四邊形，接著從相機要一張影像，接著讓操作者從該影像中描出那個四邊形
    """
    camera_node = StringProperty('datahub.dshowwebcam')

    # 從桌面 grid 中取出 quad 用
    table_grid_mm = StringProperty("table_grid_mm")
    row_shift = NumericProperty(0)
    column_shift = NumericProperty(0)

    # 相機 quad
    quad_out = StringProperty("camera_quad")

    # 目標剪裁輸出區域 (桌面 mm 座標)
    sensor_area = DictProperty()

    # 待設定的節點
    topview_node = StringProperty('datahub.topview')


    def on_enter(self):
        self._settings_sent = False
        self._grid_initialized = False
        self.anchor_y = 'center'
        self.guide = '連線中....'
        self._routine = None
        Clock.schedule_once(self._connect, 0.1)


    def _connect(self, dt):
        self.socketio_client.emit(event=self.camera_node.lower(), data='', namespace=None, callback=self._on_connect)


    def _on_connect(self, *args):
        self.anchor_y = 'top'
        self._routine = Clock.schedule_interval(self._retrieve_camera_view, 1/30)


    def on_leave(self):
        if self._routine:
            self._routine.cancel()
            self._routine = None


    def _retrieve_camera_view(self, dt):
        self.socketio_client.emit(event=self.camera_node.lower(), data='', namespace=None, callback=self._on_receive_frame)


    @mainthread
    def _on_receive_frame(self, message):
        self.ids.npimg.sio_image = message['image']
        if not self._grid_initialized:
            self.init_grideditor()
            self._grid_initialized = True

        # 畫出上視圖
        self._render_topview()
        w, h = self._topview_resolution

        if not self._settings_sent:
            self.guide = "將游標靠近四邊形頂點，按下左鍵以及方向鍵挪動之，使之與相機中看見的四邊形輪廓疊合\n" +\
                         "完成後檢查右側的上視圖，並按下 space 將設定傳送至 " + self.topview_node +\
                         "\noutput_resolution: {w} x {h}".format(w=w, h=h)
        else:
            self.guide = "已成功將設定傳送至 "+ self.topview_node +\
                         "\noutput_resolution: {w} x {h}".format(w=w, h=h)


    def init_grideditor(self, *args):        
        grideditor = self.ids.grideditor
        try:
            camera_quad = self.load_from_manager(self.quad_out)
            grideditor.load_grid(**camera_quad)
        except KeyError:
            grideditor.init_grid(shape=[2, 2])


    def _render_topview(self):
        # 計算感應邊界在相機影像中的位置
        x, y = self.sensor_area.pos
        w, h = self.sensor_area.size
        node_dict = self.ids.grideditor.node_dict
        sensor_area_in_camera_pixel = recursive_round([node_dict[it] for it in [(0, 0), (0, 1), (1, 1), (1, 0)]])   # 第一位是 row 對應 y 的改變，第二位才是對 x
        sensor_area_in_table_mm = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]                                          # 這行順序要與上一行相同
        table_to_camera_tansform = PerspectiveTransform(src_points=sensor_area_in_table_mm, dst_points=sensor_area_in_camera_pixel)

        # 計算畫面的輸出尺寸: 保持面積恆定，避免浪費效能
        image_area = cv2.contourArea(np.float32(sensor_area_in_camera_pixel))
        table_area = w * h
        output_scale = round((image_area / table_area) ** 0.5, 1)
        self._topview_resolution = [round(n * output_scale) for n in [w, h]]

        # 產生把相機影像貼到一張圖上的 homography
        crop_output_pixel = (np.float32([(0, 0), (w, 0), (w, h), (0, h)]) * output_scale).tolist()
        topview_homography = find_homography(srcPoints=sensor_area_in_camera_pixel, dstPoints=crop_output_pixel)

        self.ids.topview.numpy_image = cv2.warpPerspective(
            self.ids.npimg.numpy_image,
            topview_homography,
            self._topview_resolution,
            #flags=cv2.INTER_NEAREST,
            #borderMode=cv2.BORDER_CONSTANT,
            #borderValue=(255,255,255,255)
        )
        self._camera_to_table_quad_pairs = list(zip(sensor_area_in_camera_pixel, crop_output_pixel))


    def on_press_space(self):
        self.socketio_client.emit(
            event='set_config',
            data=dict(
                path=self.topview_node.lower(),
                config={'quad_pairs' : self._camera_to_table_quad_pairs,
                        'output_resolution' : self._topview_resolution}),
            namespace=None,
            callback=self._done_setting_callback)


    def _done_setting_callback(self, *arg):
        self._settings_sent = True


    def on_press_enter(self):
        grideditor = self.ids.grideditor
        camera_quad = recursive_round(grideditor.griddata)
        self.upload_to_manager(**{self.quad_out : camera_quad})
        self.goto_next_screen()


    def on_press_arrow(self, keyname, dxdy):
        self.ids.grideditor.move_selection(dxdy, scale=0.25)



from kivy.lang import Builder
Builder.load_string("""

<CameraQuadScreen>:

    switch_monitor_by_digitkey: True
    cursor: 'tiny cross'
    background: 0, 0, .1

    padding: 100

    AnchorLayout:
        id: editor_interface
        anchor_x: 'center'
        anchor_y: 'center'

        BoxLayout:
            size_hint: 0.8, 0.8
            orientation: 'horizontal'
            AnchorLayout:
                anchor_y: 'center'
                NumpyImage:
                    id: npimg
                    size_hint: None, None
                    size: self.texture_size
                    Scatter:
                        pos: npimg.pos
                        do_rotation: False
                        do_translation: False
                        do_scale: False
                        do_collide_after_children: True

                        GridEditor:
                            id: grideditor
                            size: npimg.size
                            pos: npimg.pos

            AnchorLayout:
                anchor_y: 'center'
                AnchorLayout:
                    anchor_y: 'center'
                    NumpyImage:
                        id: topview
                        size_hint: None, None
                        size: self.texture_size
""")