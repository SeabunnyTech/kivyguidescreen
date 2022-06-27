from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
import cv2


class NumpyImage(Widget):
    
    def __init__(self, npimage, **kwargs):
        super(Test, self).__init__(**kwargs)

        w, h, _ = npimage.shape
        texture = Texture.create(size=(w, h))
        texture.blit_buffer(npimage.flatten(), colorfmt='rgb', bufferfmt='ubyte')

        w_img = Image(size=(w, h), texture=texture)
        self.add_widget(w_img)