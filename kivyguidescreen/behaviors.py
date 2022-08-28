from kivy.clock import Clock
from kivy.core.window import Window
from screeninfo import get_monitors


class SwitchMonitorBehavior:

    @property
    def monitor_options(self):
        return get_monitors()

    def switch_to_monitor(self, monitor_option):        
        x, y, w, h = [getattr(monitor_option, name) for name in ['x', 'y', 'width', 'height']]
        Window.fullscreen = False
        Window.left = x
        Window.top = y
        self.upload_to_manager(windowsize=[w, h])
        def fullscreen(dt):
            Window.fullscreen = 'auto'
        Clock.schedule_once(fullscreen, 0.1)