from kivy.clock import Clock
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivyguidescreen import GuideScreen, GuideScreenManager

from kivyguidescreen.widgets.numpyimage import NumpyImage

import cv2
import numpy as np

from kivy.clock import Clock, mainthread


from kivy.core.window import Window


class GridInCameraScreen(GuideScreen):


    def __init__(self, camera_nodes, **kw):
        super().__init__(**kw)
        self._camera_nodes = camera_nodes

        self._ready_to_merge_view = False
        self._init_grid = False


    def on_enter(self):
        self.guide = "正在與伺服器連線中... 請稍候"

        @mainthread
        def init_guide(*arg):
            self.guide = '請將 Aruco 放到桌面中央處以設定大致的原點'

        self.socketio_client.emit(event='datahub.' + self._camera_nodes[0].lower(), data='', namespace=None, callback=init_guide)
        self._routines = [Clock.schedule_interval(self._retrive_camera_view, 1/30),
                          Clock.schedule_interval(self._ui_routine, 1/60)]


    def _ui_routine(self, dt):
        x, y = Window.mouse_pos
        if x > Window.size[0] / 2:
            self.ids.right_grideditor.disabled = True
            self.ids.left_grideditor.disabled = False
        else:
            self.ids.right_grideditor.disabled = False
            self.ids.left_grideditor.disabled = True


    def _retrive_camera_view(self, dt):
        for node_id in self._camera_nodes:
            self.socketio_client.emit(event='datahub.' + node_id.lower(), data='', namespace=None, callback=self._on_receive_camera_view(node_id))


    def _on_receive_camera_view(self, node_id):
        @mainthread
        def handle_camera_view(message):
            # 將影像顯示於畫面
            idx = self._camera_nodes.index(node_id)
            npimg_id = ['left_camera', 'right_camera'][idx]
            self.ids[npimg_id].sio_image = message['image']

            # 第一次讀到影像
            if not self._init_grid:
                self.ids.right_grideditor.init_grid(shape=(2,2))
                self.ids.left_grideditor.init_grid(shape=(2,2))
                self._init_grid = True


            # 當 Homography 準備好的時候就直接算出完整的組合影像
            if self._ready_to_merge_view:
                self._show_merged_view()

        return handle_camera_view


    def on_leave(self):
        if self._routine:
            self._routine.cancel()
            self._routine = None


    def on_press_space(self):
        self.guide = '擷取中..'
        self._left_queue = []
        self._right_queue = []
        self._ready_to_merge_view = False


    def on_press_enter(self):
        self.goto_next_screen()


    def _find_homography(self):

        # 定義找出 aruco median 的方法
        def find_median(aruco_samples):

            def coord_mediam(coords):
                from statistics import median
                x_list, y_list = zip(*coords)
                return median(x_list), median(y_list)

            four_corner_samples = zip(*aruco_samples)
            median_aruco_corners = [coord_mediam(corner_samples) for corner_samples in four_corner_samples]

            return np.array(median_aruco_corners, dtype=np.float32)

        # 將左右通道 aruco 的 median 都取出來 (已轉成 numpy array)
        left_aruco_median, right_aruco_median = [find_median(it) for it in [self._left_queue, self._right_queue]]

        # 將左右影像的 homography 都算出來
        # 頂點順序為左上右上右下左下
        r = self._output_aruco_size / 2
        ref_corners = np.array([[-r, r], [r, r], [r, -r], [-r, -r]], dtype=np.float32)
        left_homography, mask = cv2.findHomography(srcPoints=left_aruco_median, dstPoints=ref_corners)
        right_homography, mask = cv2.findHomography(srcPoints=right_aruco_median, dstPoints=ref_corners)

        # 計算左右影像邊緣被 homography 轉換的落點
        left_numpy = self.ids.left_camera.numpy_image
        h, w = left_numpy.shape[:2]
        left_image_corners = np.array([[[0, 0], [w, 0], [w, h], [0, h]]], dtype=np.float32)
        left_output_image_corners = cv2.perspectiveTransform(left_image_corners, left_homography)

        right_numpy = self.ids.right_camera.numpy_image
        h, w = right_numpy.shape[:2]
        right_image_corners = np.array([[[0, 0], [w, 0], [w, h], [0, h]]], dtype=np.float32)
        right_output_image_corners = cv2.perspectiveTransform(right_image_corners, right_homography)

        # 找出最小的 x, y 然後平移中央點的參考座標
        all_corners = left_output_image_corners[0].tolist() + right_output_image_corners[0].tolist()
        min_x = min([pos[0] for pos in all_corners])
        max_x = max([pos[0] for pos in all_corners])
        min_y = min([pos[1] for pos in all_corners])
        max_y = max([pos[1] for pos in all_corners])

        # 訂出輸出邊界以及轉換點座標
        self._merged_size = round(max_x - min_x), round(max_y - min_y)
        homography_output_corners = ref_corners - np.array([[min_x, min_y]] * 4)

        # 計算左右 homography 以及 mask
        self._left_homography, mask = cv2.findHomography(srcPoints=left_aruco_median, dstPoints=homography_output_corners)
        self._right_homography, mask = cv2.findHomography(srcPoints=right_aruco_median, dstPoints=homography_output_corners)

        self._left_mask = cv2.warpPerspective(
                np.ones_like(left_numpy) * 255,
                self._left_homography,
                self._merged_size).reshape(-1)

        self._right_mask = cv2.warpPerspective(
                np.ones_like(right_numpy) * 255,
                self._right_homography,
                self._merged_size).reshape(-1)

        self._ready_to_merge_view = True


    ### 未來這個函數應該要移除放到一個 siotypes 模組
    @staticmethod
    def sioimage_to_numpy(sioimage):
        shape = sioimage['shape']
        array = sioimage['array']

        def find_dtype(shape, array):
            if len(shape) == 3:
                dtype = np.uint8
            elif len(shape) == 2:
                h, w = shape[0:2]
                bytes_per_pixel = len(array) / (h * w)

                if bytes_per_pixel == 1:
                    dtype = np.uint8
                elif bytes_per_pixel == 2:
                    dtype = np.uint16

            return dtype

        dtype = find_dtype(shape, array)
        return np.frombuffer(array, dtype=dtype).reshape(*shape)


    @mainthread
    def _show_merged_view(self):
        self.guide = "已定位 Aruco 並轉出上視圖，檢查上視圖中的 Aruco 形狀是否接近正方形以確認其準確性"

        left_numpy = self.ids.left_camera.numpy_image
        left_topview = cv2.warpPerspective(
                left_numpy,
                self._left_homography,
                self._merged_size).reshape(-1)

        right_numpy = self.ids.right_camera.numpy_image
        right_topview = cv2.warpPerspective(
                right_numpy,
                self._right_homography,
                self._merged_size).reshape(-1)

        w, h = self._merged_size
        img = np.zeros(shape=(h, w), dtype=np.uint8).reshape(-1)
        left_idx_arr = (self._left_mask > 0) & (self._right_mask < 255)
        img[left_idx_arr] = left_topview[left_idx_arr]
        right_idx_arr = (self._right_mask > 0) & (self._left_mask < 255)
        img[right_idx_arr] = right_topview[right_idx_arr]
        merged_index_arr = (self._left_mask > 0) & (self._right_mask > 0)
        img[merged_index_arr] = (left_topview[merged_index_arr] / 2 + right_topview[merged_index_arr] /2)
        self.ids.merge_view.numpy_image = img.reshape(h, w)



from kivy.lang import Builder
Builder.load_string("""



<Scatter>:
    do_rotation: False
    do_translation: False
    do_scale: False
    do_collide_after_children: True


<GridInCameraScreen>:

    cursor: 'tiny cross'
    background: 0, 0, .1

    anchor_y: 'bottom'

    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'center'

        BoxLayout:
            orientation: 'vertical'
            size_hint: 1, 0.8
            BoxLayout:
                size_hint: 1, 1
                orientation: 'horizontal'

                NumpyImage:
                    id: right_camera
                    size: self.texture_size
                    Scatter:
                        pos: right_camera.pos
                        GridEditor:
                            id: right_grideditor
                            size: right_camera.size
                            pos: right_camera.pos

                NumpyImage:
                    id: left_camera
                    size: self.texture_size
                    Scatter:
                        pos: left_camera.pos
                        GridEditor:
                            id: left_grideditor
                            size: left_camera.size
                            pos: left_camera.pos

            NumpyImage:
                id: merge_view
""")