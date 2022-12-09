from kivy.clock import Clock
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivyguidescreen import GuideScreen, GuideScreenManager

from kivyguidescreen.widgets.numpyimage import NumpyImage

import cv2
import numpy as np

from kivy.clock import Clock, mainthread



class CameraTopviewScreen(GuideScreen):


    def __init__(self,
                 boundary,
                 output_aruco_size,
                 aruco_node='arucodetector2d',
                 draw_aruco_node='drawarucocorners',
                 **kw):

        super().__init__(**kw)
        self._boundary = boundary
        self._output_aruco_size = output_aruco_size
        self._aruco_node = (aruco_node if aruco_node.startswith('datahub.') else 'datahub.' + aruco_node).lower()
        self._draw_aruco_node = (draw_aruco_node if draw_aruco_node.startswith('datahub.') else 'datahub.' + draw_aruco_node).lower()
        self._corner_sets = []
        self._homography = None

    def on_enter(self):
        self.guide = "正在與伺服器連線中... 請稍候"

        @mainthread
        def init_guide(*arg):
            self.guide = '請將 Aruco 放到桌面中央處以設定大致的原點'

        self.socketio_client.emit(event=self._aruco_node, data='', namespace=None, callback=init_guide)
        self._routine = Clock.schedule_interval(self._retrive_aruco_view, 1/30)


    def on_leave(self):
        if self._routine:
            self._routine.cancel()
            self._routine = None

    def on_press_space(self):
        self.guide = '擷取中..'
        Clock.schedule_once(self._locate_aruco(sample_num=30), 0)


    def on_press_enter(self):
        self.goto_next_screen()
        # 準備頂點座標
        #aruco_id = list(self._corner_sets[0].keys())[0]
        #for aruco_message in self._corner_sets:
        #    assert len(aruco_message) == 1 and list(aruco_message.keys())[0] == aruco_id, "Inconsistant aruco calibrator"
        #aruco_corners = [np.array(aruco_message[aruco_id], dtype=np.float32) for aruco_message in self._corner_sets]
        return

        # 掃過整個 _corner_sets (內容是形如 {id:corners} 的 list) 統計出它們的中心座標
        aruco_centers = [sum(corners) / 4 for corners in aruco_corners]

        # 統計兩兩 aruco 中心之間的距離
        distances = {}
        for sidx, start_point in enumerate(aruco_centers):
            dist = distances[sidx] = {}
            for eidx, end_point in enumerate(aruco_centers):
                if sidx == eidx:
                    continue
                dist[eidx] = np.linalg.norm(end_point - start_point)

        # 從原點出發，將最近的 aruco 拿來納入計算
        print(distances)
        return

        def locate(aruco_corners):
            # 從已知座標的點集中找出最接近 aruco_corners 的一些點
            # 計算區域內的 homography
            # 用這個 homography 對輸入的頂點作 perspective transform 再回傳
            return relative_positions


        # 先算出所有頂點的上視座標 ( 把第一組 aruco 的座標設為原點 )
        
        
        # 於是得到一堆 {pixel_corners : mm_corners} 點對
        # 準備一個 pixel => mm 的函數，用最接近輸出處的十個以內的點搭配簡易的模型作外插
        # 將相機畫面的四角用外插法轉出 mm 座標
        # 用相機四角的 mm 座標決定輸出影像的尺寸
        # 分割輸出影像，用一群 warpPerspective 拼起來
        # 產生上視 index array 圖


    def _locate_aruco(self, sample_num):
        self._aruco_corner_samples = []
        def add_aruco_sample(message):
            if len(message['aruco_id_found']) == 1:
                self._aruco_corner_samples.append(message['corners'])

            if len(self._aruco_corner_samples) < sample_num:
                Clock.schedule_once(emit_locate_aruco, 1/30)
            else:
                self._on_done_locating_aruco()

        def emit_locate_aruco(*arg):
            self.socketio_client.emit(event=self._aruco_node, data='', namespace=None, callback=add_aruco_sample)

        return emit_locate_aruco


    def _find_homography(self, corners):
        aruco_corners = np.array(corners, dtype=np.float32)

        # 以第一組頂點為基準算出一個 homography
        # 頂點順序為左上右上右下左下
        r = self._output_aruco_size / 2
        ref_corners = np.array([[-r, r], [r, r], [r, -r], [-r, -r]], dtype=np.float32)
        camera_corners = aruco_corners
        homography_matrix, mask = cv2.findHomography(srcPoints=camera_corners, dstPoints=ref_corners)

        # 計算影像邊緣被 homography 轉換的落點
        h, w = self.ids.camera_image.numpy_image.shape[:2]
        camera_image_corners = np.array([[[0, 0], [w, 0], [w, h], [0, h]]], dtype=np.float32)
        output_image_corners = cv2.perspectiveTransform(camera_image_corners, homography_matrix)

        # 找出最小的 x, y 然後平移中央點的參考座標
        min_x = min([pos[0] for pos in output_image_corners[0]])
        max_x = max([pos[0] for pos in output_image_corners[0]])
        min_y = min([pos[1] for pos in output_image_corners[0]])
        max_y = max([pos[1] for pos in output_image_corners[0]])

        # 訂出輸出邊界以及轉換點座標
        self._output_boundary = round(max_x - min_x), round(max_y - min_y)
        homography_output_corners = ref_corners - np.array([[min_x, min_y]] * 4)

        self._homography, mask = cv2.findHomography(srcPoints=camera_corners, dstPoints=homography_output_corners)


    @mainthread
    def _on_done_locating_aruco(self):

        def coord_mediam(coords):
            from statistics import median
            x_list, y_list = zip(*coords)
            return median(x_list), median(y_list)

        # 這邊假定現在 self._aruco_corner_samples 內的 aruco 只有一個而且都是同一個
        aruco_corner_samples = [list(it.values())[0] for it in self._aruco_corner_samples]
        #print(aruco_corner_samples)
        four_corner_samples = zip(*aruco_corner_samples)
        median_aruco_corners = [coord_mediam(corner_samples) for corner_samples in four_corner_samples]

        ### _corner_sets 變數原本設計給多次採樣，但現在暫時只用一次採樣
        self._find_homography(median_aruco_corners)
        self.guide = "已定位 Aruco 並轉出上視圖，檢查上視圖中的 Aruco 形狀是否接近正方形以確認其準確性"


    def _retrive_aruco_view(self, dt):
        self.socketio_client.emit(event=self._draw_aruco_node, data='', namespace=None, callback=self._on_receive_aruco_view)


    @mainthread
    def _on_receive_aruco_view(self, message):
        self.ids.camera_image.sio_image = message['image']
        if self._homography is not None:
            sioimage = message['image']
            shape, array, dtype = [sioimage[it] for it in ['shape', 'array', 'dtype']]
            camera_image = np.frombuffer(array, dtype=dtype).reshape(*shape)
            self.ids.topview.numpy_image = cv2.warpPerspective(
                camera_image,
                self._homography,
                self._output_boundary,
                flags=cv2.INTER_NEAREST,
                #borderMode=cv2.BORDER_CONSTANT,
                #borderValue=(255,255,255,255)
            )




from kivy.lang import Builder
Builder.load_string("""



<CameraTopviewScreen>:

    cursor: 'tiny cross'
    background: 0, 0, .1

    anchor_y: 'bottom'

    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'

        BoxLayout:
            size_hint: 0.8, 0.8
            orientation: 'horizontal'

            NumpyImage:
                id: camera_image

            NumpyImage:
                id: topview

""")