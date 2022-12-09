from kivyguidescreen import GuideScreen, GuideScreenManager
from kivy.clock import Clock
from kivy.graphics import Line, Color, Rectangle, InstructionGroup
from kivy.properties import OptionProperty, NumericProperty

from kivy.core.window import Window

from math import ceil, log, floor

class GrayCodeScreen(GuideScreen):

    mode = OptionProperty('welcome', options=['welcome', 'testsensor', 'th_black', 'th_white', 'autorun', 'done'])



    def __init__(self, light_settle_time=0.2, **kw):
        super().__init__(**kw)
        self.settle_time = light_settle_time
        with self.canvas.after:
            Color(1, 1, 1)
            self.testblock_instructions = InstructionGroup()
            self.whiteband_instructions = InstructionGroup()
            Color(1, 1, 0)
            self.yellow_cross_instructions = InstructionGroup()


    def on_enter(self):
        self.show_welcome_guide()
        Clock.schedule_interval(self.draw_white_block, 1/60)


    def show_welcome_guide(self):
        w, h = self.windowsize = self.load_from_manager('windowsize')
        self.guide = '按下 Enter 後開始對 {w}x{h} 的投影機進行校正\n或按下空白鍵來測試個別感應器'.format(
            w=w,
            h=h,
        )


    def on_press_enter(self):
        if self.mode == 'welcome':
            # prepare some necessary variables for algorithm
            self.sensor_expecting_white = [True] * 6
            self.sensor_uvs = [[0, 0] for i in range(6)]
            
            w, h = self.windowsize
            from math import ceil, log, floor
            wstages = floor(log(w, 2))
            self.wstep = 2 ** wstages 
            hstages = floor(log(h, 2))
            self.hstep = 2 ** hstages

            # "draw" the black screen first
            self.yellow_cross_instructions.clear()
            self.whiteband_instructions.clear()
            self.guide = ''
            self.mode = 'th_black'
            #Clock.schedule_once(self.capture_and_schedule_next_draw, self.settle_time)
            self.graycode_index = 0
        elif self.mode == 'graycode':
            self.draw_graycode(orientation='w', width_power=10-self.graycode_index)
            self.graycode_index += 1

        elif self.mode == 'done':
            self.guide = '完成'
            self.goto_next_screen()


    def draw_graycode(self, orientation, width_power):

        # 判斷 orientation 是否正確
        orientation_options = ['vertical', 'horizontal', 'v', 'h']
        if orientation not in orientation_options:
            raise ValueError("orientation must be one of these options:", orientation_options)

        codewidth = 2 ** width_power
        print('codewidth', codewidth)
        win_w, win_h = self.windowsize

        horizontal = (orientation[0] == 'h')        
        length_to_go = win_w if horizontal else win_h
        blocksize = [codewidth, win_h] if horizontal else [win_w, codewidth]

        # 畫出所有條紋
        ins = self.whiteband_instructions
        ins.clear()
        for idx in range(length_to_go//codewidth):
            if (idx-1) % 4 < 2:
                pos = [idx * codewidth, 0] if horizontal else [0, idx * codewidth]         
                ins.add(Rectangle(pos=pos, size=blocksize))


    def capture_and_schedule_next_draw(self, dt):
        ins = self.whiteband_instructions
        ins.clear()
        
        win_w, win_h = self.windowsize
        wstep, hstep = self.wstep, self.hstep
        
        if self.mode == 'th_black':
            ins.add(Rectangle(pos=[0,0], size=self.windowsize))
            self.mode = 'th_white'
        elif self.mode == 'th_white':
            ins.add(Rectangle(pos=[wstep,0], size=[wstep, win_h]))
            self.mode = 'autorun'
        elif self.mode == 'autorun':

            if wstep > 0:
                self.draw_graycode(orientation='horizontal', width_power=ceil(log(wstep, 2)))
                wstep = self.wstep = wstep // 2
    

            elif hstep > 0:

                if hstep > 0:
                    self.draw_graycode(orientation='vertical', width_power=ceil(log(hstep, 2)))
                else:
                    self.mode = 'done'
                    self.guide = '偵測完成: 請檢查黃色十字是否正確通過每一個偵測器，按下 Enter 進入微調'

                hstep = self.hstep = hstep // 2

        if self.hstep > 0:
            Clock.schedule_once(self.capture_and_schedule_next_draw, self.settle_time)


    def on_press_space(self):
        if self.mode in ['welcome', 'testsensor']:
            self.mode = 'welcome' if self.mode == 'testsensor' else 'testsensor'
            if self.mode == 'welcome':
                self.show_welcome_guide()


    def draw_white_block(self, dt):
        ins = self.testblock_instructions
        ins.clear()
        if self.mode == 'testsensor':
            px, py = Window.mouse_pos
            ins.add(Rectangle(pos=(px-50, py-50), size=(100, 100)))

    def undo(self):
        if self.mode   in ['testsensor', 'th_black', 'th_white', 'autorun', 'done']:
            self.mode = 'welcome'
            all_ins = [
                self.testblock_instructions,
                self.whiteband_instructions,
                self.yellow_cross_instructions
            ]
            for ins in all_ins:
                ins.clear()
            self.show_welcome_guide()
        elif self.mode == 'welcome':
            self.goto_previous_screen()


from kivy.lang import Builder
Builder.load_string("""


<GrayCodeScreen>:
    show_cursor: False
    anchor_y: 'bottom'
    padding: 200



""".format(colors=GuideScreenManager.colors))
 
