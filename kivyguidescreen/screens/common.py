import os
import json

from kivy.utils import QueryDict
from kivy.clock import Clock
from kivy.core.window import Window

from .. import GuideScreenManager, GuideScreen



class SetupScreen(GuideScreen):


    def load_option(self, option):
    
        data = option['data']
    
        def setup_projector():
            self.manager.wallpaper = None
            from kivy.core.window import Window
            x, y = data['x'], data['y']
            Window.fullscreen = False
            Window.left = x
            Window.top = y
            self.upload_to_manager(windowsize=[data.w, data.h])
            def fullscreen(dt):
                Window.fullscreen = 'auto'
            Clock.schedule_once(fullscreen, 0.1)

        def setup_kinectv2():
            from irview import KinectV2IRView
            if '_kinect_ir_view' not in dir(self):
                self._kinect_ir_view = KinectV2IRView(size_hint=[None, None], size=[1024, 848])
                self._kinect_ir_view.start()
            self.manager.wallpaper = self._kinect_ir_view

        func = dict(
            kinectv2=setup_kinectv2,
            projector=setup_projector,
        )[data['device_type']]

        func()
        


    def generate_monitor_options(self):
        from screeninfo import get_monitors
        options = []

        for m in get_monitors():
            data = QueryDict(
                device_type='projector',
                resolution=[m.width, m.height],
                w=m.width,
                h=m.height,
                x=m.x,
                y=m.y,
            )
            guidetext = '將視窗移至顯示器 {name}  w={w}, h={h}  @  x={x}, y={y}'.format(
                name=m.name.split('\\')[-1],
                **data
            )
            options.append(QueryDict(
                guidetext=guidetext,
                data=data,
            ))

        return options


    def generate_kinectv2_options(self):

        return [
            QueryDict(
                guidetext='Kinect V2',
                data=dict(
                    device_type='kinectv2',
                    resolution=[512, 424],
                ),
            )
        ]


    @property
    def options(self):
        options = []
        options += self.generate_monitor_options()
        #options += self.generate_kinectv2_options()
        
        ret_options = {}
        for idx, opt in enumerate(options):
            key = str(idx+1)
            ret_options[key] = opt
        return ret_options


    def on_enter(self):
        self.ids.guidelabel.halign = 'left'
        self.guide = '請輸入數字選擇校正的目標:\n\n'
        for key, opt in self.options.items():
            self.guide += '   ' + key + ' : ' + opt.guidetext + '\n'


    def on_key_down(self, keyname, modifiers):
        options = self.options
        if keyname.isdigit():
            if keyname in options:
                opt = options[keyname]
                self.load_option(opt)
                self.upload_to_manager(calibrate_option=opt.data)


    def on_press_enter(self):
        self.goto_next_screen()



class LoadAutoSaveScreen(GuideScreen):

    def on_enter(self):
        if not os.path.isfile(self.manager.tempfile):
            self.goto_next_screen()


    def on_key_down(self, keyname, modifiers):
        if keyname not in ['0', 'numpad0']:
            self.load_autosave()
        else:
            self.goto_next_screen()


    def load_autosave(self):
        with open(self.manager.tempfile) as tempfile:
            temp_settings = json.load(tempfile)

        self.manager.load_settings(temp_settings)





from kivy.lang import Builder
Builder.load_string("""

#:import Window kivy.core.window.Window


<SetupScreen>:
    show_cursor: False
    #background: {colors.Y}
    autosave: False


<LoadAutoSaveScreen>:
    background: {colors.C}
    guide: '是否要接續上次中斷的校正程序呢?\\n按 0 跳過，按其他任意鍵載入'
    autosave: False

""".format(colors=GuideScreenManager.colors))