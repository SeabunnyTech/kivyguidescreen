from kivy.uix.screenmanager import ScreenManager, FadeTransition, Screen
from kivy.properties import BooleanProperty, ListProperty, StringProperty, OptionProperty, ObjectProperty, DictProperty
from kivy.graphics import InstructionGroup, Line, Color

from kivy.utils import QueryDict

import os
import json

from kivy.core.window import Window
from kivy.base import stopTouchApp

Window.show_cursor = False

# set traditional chinese font
from kivy.resources import resource_add_path
pkgpath = os.path.dirname(__file__)
resource_add_path(pkgpath)



class GuideScreenManager(ScreenManager):

    guidescreens = ListProperty([])

    colors = QueryDict({
        'C' : [.2, .7, .7],
        'Y' : [.7, .7, .2],
        'M' : [.7, .2, .7],
        'darkgray' : [.2, .2, .2],
        'green': [.2, .7, .2],
    })

    title = StringProperty('')

    settings = QueryDict({})

    _subpixel_cursor = ListProperty([0, 0])

    wallpaper = ObjectProperty(None, allownone=True)

    default_address = StringProperty('http://localhost:8080')
    #default_address = StringProperty('http://192.168.0.11:8080') # 泓軒電腦
    #default_address = StringProperty('http://192.168.0.19:8080') # left
    #default_address = StringProperty('http://192.168.0.18:8080') # 台電機器

    def __init__(self, **kw):
        super(GuideScreenManager, self).__init__(**kw)

        if self.title is None:
            self.tempfile = type(self).__name__.lower() + '.json'
        else:
            Window.set_title(self.title)
            self.tempfile = self.title.replace(' ', '').lower() + '.json'

        # add crosshair to mouse
        Window.bind(mouse_pos=self.on_mouse_pos)
        with self.canvas.after:
            self.crosshair = InstructionGroup()
        
        # keyboard
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

        # binds
        self.bind(current=self.update_cursor_state)
        self.bind(on_enter=self.update_cursor_state)

        # switch to first screen
        self.transition = FadeTransition(duration=0.1)
        
        # socketio serve stuff
        self.socketio_clients = {}
        self.socketio_client_screen_map = {}

        Window.bind(on_close=self.on_window_closed)

        # 載入所有畫面，並從頭開始
        for sc in self.guidescreens:
            self.add_widget(sc)

        self.current = self.guidescreens[0].name


    def on_window_closed(self, *arg):
        for client in self.socketio_clients.values():
            client.disconnect()



    def socketio_client(self, screen):
        try:
            return self.socketio_client_screen_map[screen]
        except KeyError:
            return self.connect_socketio_server(screen)



    def connect_socketio_server(self, screen, address=None):

        if address is None:
            address = self.default_address

        import socketio
        
        if address in self.socketio_clients:
            sio = self.socketio_clients[address]
        else:
            self.socketio_clients[address] = sio = socketio.Client()
            sio.connect(address)

        self.socketio_client_screen_map[screen] = sio

        return sio



    def load_settings(self, settings):
        self.settings = QueryDict(settings)
        screen_to_go = self.get_screen(settings['current'])
        screen_to_go.unfreeze(settings['screen_state'])
        self.current = settings['current']


    def moveCursor(self, dx, dy):
        from kivy.utils import platform
        if platform == 'win':
            import win32api
            x, y = win32api.GetCursorPos()

            ############# WIER PROBELM: SetCursorPos fail to move one pixel sometimes
            nx, ny = win32api.GetCursorPos()
            if [nx, ny] == [x, y]:
                win32api.SetCursorPos((x + 2 *dx, y + 2 * dy))
        elif platform == 'linux':
            import pyautogui
            x, y = pyautogui.position()
            pyautogui.moveTo( x + dx, y + dy )
        else:
            raise NotImplementedError


    def update_cursor_state(self, *args):
        self.on_mouse_pos(None, Window.mouse_pos)

    @property
    def subpixel_cursor(self):
        return self._subpixel_cursor[:]


    def on_mouse_pos(self, caller, pos):
        self._subpixel_cursor[:] = pos


    def on__subpixel_cursor(self, *args):
        if 'show_cursor' in dir(self.current_screen) and self.current_screen.show_cursor is False:
            self.crosshair.clear()
            return
        
        x, y = self._subpixel_cursor
        self.crosshair.clear()
        self.crosshair.add(Color(1, 1, 1))
        self.crosshair.add(Line(points=[x, 0, x, Window.height], width=0.25))
        self.crosshair.add(Line(points=[0, y, Window.width, y], width=0.25))


    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None



    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):

        mouse_dxdy = {
            'up'    : (0, 1),
            'down'  : (0, -1),
            'left'  : (-1, 0),
            'right' : (1, 0)
        }
        
        keyname = keycode[1]
        if keyname.startswith('numpad'):
            keyname = keyname[6:]
            if keyname == 'decimal':
                keyname = '.'
            if self.current_screen.numpad_as_arrows and keyname in ['2', '4', '6', '8']:
                keyname = {'2':'down', '4':'left', '6':'right', '8':'up'}[keyname]

        if keyname in ['up', 'down', 'left', 'right']:
            dx, dy = mouse_dxdy[keyname]
            px, py = self._subpixel_cursor
            self._subpixel_cursor[:] = px + dx*0.25, py + dy*0.25
            if 'on_press_arrow' in dir(self.current_screen):
                self.current_screen.on_press_arrow(keyname=keyname, dxdy=[dx, dy])
            return True
        else:
            mapping = {'enter':'on_press_enter', 'backspace':'undo', 'spacebar':'on_press_space', 'tab':'on_press_tab'}

            if keyname in mapping:
                shortcut_func_name = mapping[keyname]

            if (keyname in mapping) and (shortcut_func_name in dir(self.current_screen)):
                func = getattr(self.current_screen, shortcut_func_name)
                return func()
            elif 'on_key_down' in dir(self.current_screen):
                return self.current_screen.on_key_down(keyname, modifiers)


    def autosave(self, *args):
        if self.current_screen.autosave is False:
            return
        self.save_settings(self.tempfile)


    def save_settings(self, filename):
        self.settings.current = self.current
        self.settings.screen_state = self.current_screen.freeze()
        try:
            # could fail here
            with open(filename + '.bak', 'w') as tempfile:
                json.dump(self.settings, tempfile, indent=4)
            # delete previous autosave file and replace it
            if os.path.isfile(filename):
                os.remove(filename)
            os.rename(filename + '.bak', filename)
        except:
            import traceback
            traceback.print_exc()
            # remove corrupted file
            os.remove(filename + '.bak')


    def on_wallpaper(self, caller, wallpaper):

        def pass_wallpaper(caller, screen):
            if wallpaper.parent is not None:
                wallpaper.parent.remove_widget(wallpaper)
            if screen.accept_wallpaper:
                screen.set_wallpaper(wallpaper)

        # bind switching action to screen change
        if wallpaper is not None:
            self.bind(current_screen=pass_wallpaper)
        else:
            self.unbind(current_screen=pass_wallpaper)

        # add / remove wall paper now
        if self.current_screen.accept_wallpaper:
            self.current_screen.set_wallpaper(wallpaper)



class GuideScreen(Screen):

    background = ListProperty([0, 0, 0])

    # position the guide text
    anchor_x = OptionProperty('center', options=['left', 'center', 'right'])
    anchor_y = OptionProperty('center', options=['top', 'center', 'bottom'])
    guide = StringProperty('')

    # 變數命名設定
    remap_vars = DictProperty({})

    # some handy settings
    show_cursor = BooleanProperty(True)
    accept_wallpaper = BooleanProperty(False)
    autosave = BooleanProperty(True)
    numpad_as_arrows = BooleanProperty(False)

    def __init__(self, **kw):
        self.state = QueryDict({})
        if 'name' not in kw:
            kw['name'] = self.__class__.__name__.lower()
        super(GuideScreen, self).__init__(**kw)

    def freeze(self):
        self.state.update({'show_cursor' : self.show_cursor})
        return self.state

    def unfreeze(self, state):
        self.state = QueryDict(state)
        self.show_cursor = self.state.show_cursor

    def on_arrow_pressed(self, keyname, dxdy):
        pass

    def on_show_cursor(self, *args):
        if self.manager is not None:
            self.manager.update_cursor_state()

    def goto_next_screen(self, *args):
        if self.manager.current_screen == self.manager.screens[-1]:
            stopTouchApp()
        self.manager.current = self.manager.next()

    def undo(self):
        self.goto_previous_screen()

    def goto_previous_screen(self, *args):
        self.manager.current = self.manager.previous()

    def load_from_manager(self, varname):
        if varname in self.remap_vars:
            varname = self.remap_vars[varname]
        return self.manager.settings[varname]
    
    def upload_to_manager(self, overwrite=False, **kw):

        # 重訂變數名
        for original_name in self.remap_vars:
            new_name = self.remap_vars[original_name]
            kw[new_name] = kw.pop(original_name)

        self.manager.settings.update(kw)

    def save_settings(self, filename):
        self.manager.save_settings(filename)

    def set_wallpaper(self, wallpaper_widget):
        self.ids.wallpaperlayer.clear_widgets()
        if wallpaper_widget is None:
            return

        if wallpaper_widget.parent is not None:
            wallpaper_widget.parent.remove_widget(wallpaper_widget)

        self.ids.wallpaperlayer.add_widget(wallpaper_widget)

    def connect_socketio_server(self, address=None):
        if address is not None:
            self.manager.connect_socketio_server(self, address=address)
        else:
            self.manager.connect_socketio_server(self)

    @property
    def subpixel_cursor(self):
        return self.manager.subpixel_cursor

    @property
    def socketio_client(self):
        return self.manager.socketio_client(self)



from kivy.lang import Builder
Builder.load_string("""

<Label, Button, TextInput>:
    font_name: 'fonts/NotoSansCJKtc-Regular.otf'
    markup: True
    font_size: '20sp'
    halign: 'center'


<GuideScreen>:
    padding: 20
    canvas:
        Color:
            rgb: root.background
        Rectangle:
            pos: 0, 0
            size: self.size

    AnchorLayout:
        id: wallpaperlayer
        anchor_x: root.anchor_x
        anchor_y: root.anchor_y

    AnchorLayout:
        id: guidelayer
        padding: root.padding
        anchor_x: root.anchor_x
        anchor_y: root.anchor_y
        Label:
            id: guidelabel
            size_hint: None, None
            size: self.texture_size
            anchor_y: 'top'
            color: [0, 0, 0] if sum(root.background) > 1.5 else [1, 1, 1]
            text: root.guide

""")