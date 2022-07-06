from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
import cv2
import numpy as np


class NumpyImage(Widget):
    
    def __init__(self, npimage, **kwargs):
        super().__init__(**kwargs)

        # 記下各種重要資訊
        w, h = self.shape = [npimage.shape[i] for i in [0, 1]]

        # 看 shape 決定顏色格式
        colorfmt = None
        if len(npimage.shape) == 2:
            colorfmt = 'rgb'
            npimage = cv2.cvtColor(npimage, cv2.COLOR_GRAY2RGB)

        elif len(npimage.shape) == 3:
            num_channels = npimage.shape[2]
            colorfmt = {3:'rgb', 4:'rgba'}[num_channels]

        # 產生 Texture 並將 numpy array 灌進去
        texture = Texture.create(size=(h, w), colorfmt=colorfmt, bufferfmt='ubyte')
        texture.blit_buffer(npimage.flatten(), colorfmt=colorfmt, bufferfmt='ubyte')

        # 把影像交給 image
        w_img = Image(size=(h, w), texture=texture)
        self.add_widget(w_img)