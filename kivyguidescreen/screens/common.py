import os
import json

from kivy.core.window import Window
from .. import GuideScreenManager, GuideScreen


class SelectMonitorScreen(GuideScreen):

    def on_touch_down(self, touch):
        self.fullscreen_and_next()

    def on_key_down(self, keyname, modifiers):
        self.fullscreen_and_next()

    def fullscreen_and_next(self):
        Window.fullscreen = 'auto'
        self.manager.settings.window_size = Window.size
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


<SelectMonitorScreen>:
    background: {colors.M}
    guide: '將這個視窗拖曳至投影上，用滑鼠點選任意處進入全螢幕'
    autosave: False



<LoadAutoSaveScreen>:
    background: {colors.C}
    guide: '是否要接續上次中斷的校正程序呢?\\n按 0 跳過，按其他任意鍵載入'
    autosave: False

""".format(colors=GuideScreenManager.colors))