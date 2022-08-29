from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
import cv2
import numpy as np

from kivy.properties import NumericProperty, ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.relativelayout import RelativeLayout



class NumpyImage(Image):
    
    numpy_image = ObjectProperty(None, force_dispatch=True)
    sio_image = ObjectProperty(None, force_dispatch=True)

    vertical_flip = BooleanProperty(False)
    horizontal_flip = BooleanProperty(False)

    def __init__(self, numpy_image=None, sio_image=None, **kwargs):
        super().__init__(**kwargs)

        self._texture = None
        self._resolution = None
        self._colorfmt = None

        if numpy_image is not None:
            self.numpy_image = numpy_image

        if sio_image is not None:
            self.sio_image = sio_image


    def on_numpy_image(self, *args):
        img = self.numpy_image

        # 16bit 的影像通常來自深度相機，而且它只會用到 12 bit
        # 此時捨棄後 4bit 轉換成 8bit 灰階影像再顯示
        if img.dtype == np.uint16:
            img = np.uint8(img.clip(1, 4000)/16.)

        # 訂出顏色種類
        shape = img.shape
        h, w = shape[:2]
        num_channels = 1 if len(shape) == 2 else shape[2]
        colorfmt = {1:'luminance', 3:'rgb', 4:'rgba'}[num_channels]

        # 初始化 texture
        if self._resolution != (w, h) or self._colorfmt != colorfmt:
            self._texture = Texture.create(size=(w, h), colorfmt=colorfmt, bufferfmt='ubyte')
            if self.vertical_flip:
                self._texture.flip_vertical()
            if self.horizontal_flip:
                self._texture.flip_horizontal()
            self._resolution = (w, h)
            self._colorfmt = colorfmt
        
        # 將圖片填入 gpu texture
        self._texture.blit_buffer(img.flatten(), colorfmt=colorfmt, bufferfmt='ubyte')

        # 把影像交給 image
        self.texture = self._texture
        self.canvas.ask_update()


    def on_sio_image(self, *args):
        img = self.sio_image
        shape, array, dtype = [img[it] for it in ['shape', 'array', 'dtype']]
        self.numpy_image = npimage = np.frombuffer(array, dtype=dtype).reshape(*shape)

