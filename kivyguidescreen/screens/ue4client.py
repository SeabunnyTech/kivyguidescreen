from kivy.properties import StringProperty

from kivyguidescreen import GuideScreen
from kivyguidescreen.widgets.numpyimage import NumpyImage

from kivy.clock import Clock, mainthread


class NumpyImageScreen(GuideScreen):

    """
    顯示某節點上的 numpy image 影像
    """

    source_node = StringProperty('datahub.dshowwebcam')

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(on_enter=self._on_enter)
        self.bind(on_leave=self._on_leave)


    def _on_enter(self, caller):
        self._routine = None
        Clock.schedule_once(self._connect, 0.1)


    def _connect(self, dt):
        self.socketio_client.emit(event=self.source_node.lower(), data='', namespace=None, callback=self._on_connect)


    def _on_connect(self, *args):
        self.anchor_y = 'top'
        self._routine = Clock.schedule_interval(self._retrieve_camera_view, 1/30)
        self.on_connect(*args)


    def on_connect(self, *args):
        pass


    def _on_leave(self, caller):
        if self._routine:
            self._routine.cancel()
            self._routine = None


    def _retrieve_camera_view(self, dt):
        self.socketio_client.emit(event=self.source_node.lower(), data='', namespace=None, callback=self._on_receive_frame)


    @mainthread
    def _on_receive_frame(self, message):
        self.ids.npimg.sio_image = message['image']
        self.on_receive_frame(message)


    def on_receive_frame(self, message):
        pass


    def on_press_enter(self):
        grideditor = self.ids.grideditor
        camera_quad = recursive_round(grideditor.griddata)
        self.upload_to_manager(**{self.quad_out : camera_quad})
        self.goto_next_screen()





from kivy.lang import Builder
Builder.load_string("""

<NumpyImageScreen>:

    switch_monitor_by_digitkey: True
    cursor: 'tiny cross'
    background: 0, 0, .1

    padding: 100

    AnchorLayout:
        id: editor_interface
        anchor_x: 'center'
        anchor_y: 'center'

        NumpyImage:
            id: npimg
            size_hint: None, None
            size: self.texture_size
""")