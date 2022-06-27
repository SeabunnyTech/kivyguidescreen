from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
import cv2
import numpy as np


class NumpyImage(Widget):
    
    def __init__(self, npimage, **kwargs):
        super().__init__(**kwargs)

        w, h = [npimage.shape[i] for i in [0, 1]]
        texture = Texture.create(size=(h, w), colorfmt='rgb', bufferfmt='ubyte')
        
        if len(npimage.shape) < 3:
            npimage = cv2.cvtColor(npimage, cv2.COLOR_GRAY2RGB)

        texture.blit_buffer(npimage.flatten(), colorfmt='rgb', bufferfmt='ubyte')

        w_img = Image(size=(h, w), texture=texture)
        self.add_widget(w_img)