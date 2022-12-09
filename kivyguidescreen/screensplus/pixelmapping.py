import numpy as np
import cv2

from kivy.clock import Clock
from kivy.properties import OptionProperty, NumericProperty
from kivyguidescreen import GuideScreen, GuideScreenManager
from kivyguidescreen.widgets.numpyimage import NumpyImage

from kivyguidescreen.widgets.grideditor import GridEditor


class PixelMappingScreen(GuideScreen):

    mode = OptionProperty(None, options=[None, 'homography', 'verify'])
    corner_offset = NumericProperty(200)


    def on_enter(self):
        of = self.corner_offset
        w, h = self.windowsize = self.load_from_manager('windowsize')
        self.npimage = None

        # 載入先前準備的 griddata 或者初始化一份出來
        try:
            griddata = self.load_from_manager('mapping_grid')
        except KeyError:
            griddata = dict(
                size=(2, 2),
                nodes = [
                    ((of, of), (0, 0)),
                    ((w - of, of), (w, 0)),
                    ((of, h - of), (0, h)),
                    ((w - of, h - of), (w, h)),
                ]
            )

        # 產生 GridEditor Widget
        self._grideditor = grideditor = GridEditor(griddata=griddata)
        self.add_widget(grideditor)
        self.mode = 'homography'


    def on_mode(self, newmode, caller):
        self.show_cursor = self.mode == 'homography'
        if self.mode == 'homography':
            self.guide = '將滑鼠靠近四角的標記，以左鍵或上下左右鍵對標記位置做微調以符合矩形的桌面\n完成後按 Enter 觀看矩形輔助線'
            self._grideditor.disabled = False
            self.update_routine = Clock.schedule_interval(self.update, 0)
        elif self.mode == 'verify':
            self._grideditor.update_canvas(cursor_position=None)
            self.guide = '檢查畫面中的直線 1.有無彎曲 以及 2. 長度是否相同 來確認校正結果'
            self._grideditor.disabled = True
            self.update_routine.cancel()


    def on_leave(self):
        self.update_routine.cancel()


    def update(self, _):
        if self.mode == 'homography':
            self._grideditor.update_canvas(cursor_position=self.manager.subpixel_cursor)


    def on_press_arrow(self, keyname, dxdy):
        if self.mode == 'homography':
            self._grideditor.move_selection(dxdy)


    def generate_test_pattern(self):
        # 在等同螢幕解析度的影像上畫出一些直線
        # 並以顏色區分長度
        w, h = self.windowsize
        img = np.full(shape=(h,w,3), fill_value=100, dtype=np.uint8)

        import random
        for i in range(100):
            x0 = random.randint(0,w-1)
            y0 = random.randint(0,h-1)
            
            arrow = 500 * (1j ** random.uniform(0, 4))
            dy = arrow.imag
            dx = arrow.real
            if 0 < x0 + dx < w and 0 < y0 + dy < h:
                cv2.line(img, (x0, y0), (int(x0+dx), int(y0+dy)), (255, 255, 0), 2)

        return img


    def xygrid_to_bgra_pixelmap(self, xarr, yarr):
        h, w = xarr.shape
        B_arr = xarr // 256
        G_arr = xarr % 256
        R_arr = yarr // 256
        A_arr = yarr % 256

        mix_arr = np.zeros(shape=(h, w, 4), dtype=np.uint8)
        mix_arr[:, :, 0] = B_arr
        mix_arr[:, :, 1] = G_arr
        mix_arr[:, :, 2] = R_arr
        mix_arr[:, :, 3] = A_arr

        return mix_arr


    def bgra_pixelmap_to_index_array(self, bgra_image_pixelmap):
        h, w, _ = bgra_image_pixelmap.shape
        B_arr, G_arr, R_arr, A_arr = [bgra_image_pixelmap[:,:,idx].astype(np.uint32) for idx in range(4)]

        x_arr = B_arr * 256 + G_arr
        y_arr = R_arr * 256 + A_arr
        arr = y_arr * w + x_arr

        return arr


    def pixelwise_transform(self, image, pixelmap):
        w, h = self.windowsize
        mask_num = 65535 * (w + 1)
        index_array = self.bgra_pixelmap_to_index_array(pixelmap)

        mask = np.ones_like(index_array)
        mask[index_array == mask_num] = 0

        index_array[index_array == mask_num] = 0
        origin_shape = image.shape

        # 攤平然後用 index 做 remapping
        if len(origin_shape) == 2:
            image = image.reshape(-1)
        elif len(origin_shape) == 3:
            image = image.reshape(-1, origin_shape[2])

        image = image[index_array.astype(np.uint32)].reshape(*origin_shape)
        image[mask == 0] = 0
        return image


    def on_press_enter(self):
        if self.mode == 'homography':
            self.upload_to_manager(mapping_grid=self._grideditor.griddata)
            self.mode = 'verify'

            # 產生 pixelmap 並且拿它來轉換一張測試圖像
            #pixelmap = self._compute_pixelmap()
            self.pixelmap = pixelmap = self._test_pixelmap()
            test_pattern = self.generate_test_pattern()
            verifycation_image = self.pixelwise_transform(test_pattern, pixelmap)

            # 如果先前已經生成過 npimage，重新產生時要把上一張圖移除
            if self.npimage:
                self.remove_widget(self.npimage)

            # 顯示確認影像
            self.npimage = img = NumpyImage(verifycation_image)
            #self.npimage = img = NumpyImage(pixelmap)
            self.add_widget(img, len(self.children))

        elif self.mode == 'verify':
            self.upload_to_manager(pixelmap=self.pixelmap)
            self.goto_next_screen()


    def undo(self):
        if self.mode == 'homography':
            self.goto_previous_screen()
        elif self.mode == 'verify':
            self.mode = 'homography'


    def _test_pixelmap(self):
        # 取出四角，算出 homography
        w, h = self.windowsize
        grid = self._grideditor._mapping_grid

        M, status = cv2.findHomography(
            np.array([[0,0], [w-1,0], [0,h-1], [w-1,h-1]]),
            np.array(grid.corners),
        )

        # 產生基本的 mgrid
        yarr, xarr = np.mgrid[0:h,0:w]
        bgra_pixelmap = self.xygrid_to_bgra_pixelmap(xarr, yarr)

        return cv2.warpPerspective(bgra_pixelmap, M, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,255,255))


    def _compute_pixelmap(self):
        # 預計從格點算出模型 pixelmap
        grid = self._mapping_grid
        n_row, n_col = grid.size()

        # 產生基本的 mgrid
        yarr, xarr = np.mgrid[0:h,0:w]
        bgra_pixelmap = self.xygrid_to_bgra_pixelmap(xarr, yarr)

        # 根據 n_row 及 n_col 分割 mgrid，再一小區一小區地做 homography?
        return arr



from kivy.lang import Builder
Builder.load_string("""

<PixelMappingScreen>:
    background: .1, .2, .3

""")

