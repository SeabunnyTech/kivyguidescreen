from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
import cv2
import numpy as np

from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.relativelayout import RelativeLayout



class NumpyImage(Image):
    
    numpy_image = ObjectProperty(None, force_dispatch=True)
    sio_image = ObjectProperty(None, force_dispatch=True)

    def __init__(self, numpy_image=None, sio_image=None, **kwargs):
        super().__init__(**kwargs)

        if numpy_image is not None:
            self.numpy_image = numpy_image

        if sio_image is not None:
            self.sio_image = sio_image


    def on_numpy_image(self, *args):
        img = self.numpy_image

        # 記下各種重要資訊
        w, h = self.shape = [img.shape[i] for i in [0, 1]]

        # 看 shape 決定顏色格式
        colorfmt = None
        if len(img.shape) == 2:
            colorfmt = 'rgb'
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        elif len(img.shape) == 3:
            num_channels = img.shape[2]
            colorfmt = {3:'rgb', 4:'rgba'}[num_channels]

        # 產生 Texture 並將 numpy array 灌進去
        texture = Texture.create(size=(h, w), colorfmt=colorfmt, bufferfmt='ubyte')
        texture.blit_buffer(img.flatten(), colorfmt=colorfmt, bufferfmt='ubyte')
        #texture.flip_vertical()

        # 把影像交給 image
        self.size = (h, w)
        self.texture = texture


    def on_sio_image(self, *args):
        img_var = self.sio_image
        shape = img_var['shape']
        array = img_var['array']
        if len(shape) == 3:
            npimage = np.frombuffer(array, dtype=np.uint8).reshape(*shape)
        elif len(shape) == 2:
            npimage = np.frombuffer(array, dtype=np.uint16).reshape(*shape)

        self.numpy_image = npimage


