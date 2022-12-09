from kivy.clock import Clock
from kivy.properties import NumericProperty, ListProperty, StringProperty, ColorProperty, OptionProperty
from kivy.uix.scatter import Scatter
from kivy.uix.label import Label
from kivy.graphics import Line, Color, InstructionGroup

from kivyguidescreen import GuideScreen, GuideScreenManager
from kivyguidescreen.widgets.grideditor import Grid

import numpy as np
from numpy.linalg import norm

from kivy.uix.widget import Widget


class LineSegment(Widget):

    normal_color = ColorProperty([0.5, 0.5, 1])
    selected_color = ColorProperty([1, 0.8, 1])
    error_color = ColorProperty([1, 0.5, 0.2])
    
    text = StringProperty('')
    state = OptionProperty('normal', options=['normal', 'selected', 'error'])

    def __init__(self, points, **kw):
        super().__init__(**kw)
        self._points = points
        self.ids.length_label.core_text = self.text
        self.render()

    def render(self):
        # 清空
        canvas = self.canvas.before
        canvas.clear()

        # 挑顏色
        color = {
            'normal' : self.normal_color,
            'selected' : self.selected_color,
            'error' : self.error_color,
        }[self.state]
        canvas.add(Color(*color))

        # 畫線
        p1, p2 = [np.array(p) for p in self._points]
        canvas.add(Line(points=p1.tolist() + p2.tolist()))

        # 順便將顏色指定給 Label
        self.ids.length_label.text_color = color

        # 指定位置
        self.ids.length_label.pos = ((p1+p2)/2).tolist()


    def min_distance(self, xy):
        # 將數字轉成 numpy array 方便加減
        p1, p2 = [np.array(p) for p in self._points]
        s = np.array(xy)
        
        # 位在鈍角上的頂點是最近的點，都沒有鈍角則最近點是垂足
        if np.dot(s-p1, p2-p1) < 0:
            dist = norm(s-p1)
        elif np.dot(s-p2, p1-p2) < 0:
            dist = norm(s-p2)
        else:
            dist = norm(np.cross(p1-s, p2-s))/norm(p2-p1)

        return dist



class ColorLabel(Label):

    core_text = StringProperty('')
    text_color = ColorProperty([0.5, 0.5, 1])

    def _render(self, *args):
        from kivy.utils import get_hex_from_color
        # 產生顏色 hex 碼
        color_code = get_hex_from_color(self.text_color)

        # 組合成帶有顏色碼的 markdown 文字
        self.text = '[color=' + color_code + ']' + self.core_text + '[/color]'


class VertexLabel(Label):
    pass


class MeasureGridScreen(GuideScreen):

    '''
    1. 這個頁面會載入一個四邊形，然後根據滑鼠所在的位置選擇目前要測量的邊
    2. 測完四邊以及一條對角線以後，會算出第二條對角線的長度以供驗證
    3. 確認完畢後將以底邊為 x 軸、以 mm 為單位算出每一個頂點的桌面位置，座標軸的中心會訂在兩條對角線交叉點處。
    4. 本頁面最後將輸出四個頂點的真實座標
    '''

    _error_count = NumericProperty(0)
    guide_state = OptionProperty('on_enter', options=['typing', 'typingNA', 'error_found', 'on_enter', 'almost_done'])

    display_grid = StringProperty('griddata_pixel')
    grid_out = StringProperty('griddata_mm')
    measurements = StringProperty('measured_lengths')

    def _line_segment_id(self, row1, col1, row2, col2):
        # 確保順序正確，讓 AB 和 BA 選到同一條線
        if row1 > row2:
            row1, col1, row2, col2 = row2, col2, row1, col1
        elif row1 == row2 and col1 > col2:
            row1, col1, row2, col2 = row2, col2, row1, col1
        return ','.join([str(it) for it in [row1, col1, row2, col2]])


    def on_enter(self):
        # 載入節點
        display_grid = self.load_from_manager(self.display_grid)
        row_num, col_num = self._row_num, self._col_num = display_grid['shape']
        coords = display_grid['coords']

        def coord(row, col):
            return coords[row * col_num + col]

        # 標記頂點名稱
        self._vertex_label = []
        for row in range(row_num):
            for col in range(col_num):
                label = VertexLabel(text='P[' + str(row) + ',' + str(col) + ']', pos=coord(row, col))
                self._vertex_label.append(label)
                self.add_widget(label)

        # 在邊線上放置長度標籤: 讀取紀錄
        try:
            measured_lengths = self.load_from_manager(self.measurements)
        except KeyError:
            measured_lengths = {}

        def length_text(row1, col1, row2, col2):
            key = self._line_segment_id(row1, col1, row2, col2)
            if key in measured_lengths:
                return measured_lengths[key]
            else:
                return 'NA'

        # 創造出所有的 line segment
        self._line_segments = {}

        def add_line_segment(row, col, delta_row, delta_col):
            dr, dc = delta_row, delta_col
            line_seg = LineSegment(
                points=[coord(row, col), coord(row + dr, col + dc)],
                text=length_text(row, col, row + dr, col + dc),
            )
            id = self._line_segment_id(row, col, row + dr, col + dc)
            self._line_segments[id] = line_seg
            self.add_widget(line_seg)

        # 依序加入線條
        for row in range(row_num):
            for col in range(col_num):
                # 連接節點與上一欄的節點
                if row > 0:
                    add_line_segment(row, col, -1, 0)
                # 連接節點與上一列的節點
                if col > 0:
                    add_line_segment(row, col, 0, -1)
                # 連接通往右下方的斜邊
                if row > 0 and col < col_num - 1:
                    add_line_segment(row, col, -1, 1)

        # 開始固定更新畫面
        self.update_routine = Clock.schedule_interval(self.update, 1/60)


    def update(self, dt):
        # 把每一條線的狀態訂出來
        for line in self._line_segments.values():
            if line.state != 'error':
                line.state = 'normal'

        # 即時更新選擇的線
        self._selected_line.state = 'selected'


    @property
    def _selected_line(self):
        # 找到距離游標最近的線當作 selected_line
        min_dist = 100000
        closest_line = None
        for line in self._line_segments.values():
            dist = line.min_distance(self.manager.subpixel_cursor)

            if dist < min_dist:
                min_dist = dist
                closest_line = line

        return closest_line


    @property
    def current_line_label(self):
        return self._length_labels[self._closest_line_index()]


    @property
    def measured_lengths(self):
        return {key:line.text for key, line in self._line_segments.items()}


    def on_key_down(self, keyname, modifiers):
        line = self._selected_line
        if keyname.isdigit() or keyname == '.':
            if line.text == 'NA':
                line.text = ''

            line.text += keyname

            self.upload_to_manager(**{self.measurements : self.measured_lengths})

        self.guide_state = 'typing'

        # 檢查是否所有的邊都已經被輸入數字
        for line in self._line_segments.values():
            if not self.is_legal_length(line.text):
                return

        # 所有的邊都已經數字才會抵達這裡
        self.guide_state = 'almost_done'


    def is_legal_length(self, text):
        return text.replace('.','',1).isdigit()


    def on_guide_state(self, *args):
        self.guide = {
            'typing' : '輸入中.. 按 backspace 可以刪除一個數字',
            'typingNA' : '直接輸入數字以記錄長度，按 backspace 以回到上一頁',
            'error_found' : '尚有 ' + str(self._error_count) + ' 條邊沒有被正確測量，請檢查所有被標示為橘紅色的長度值',
            'on_enter' : "將游標靠近任一條線以選擇之，接著在鍵盤上輸入其長度 (mm)\\n輸入完成時直接將游標靠近其它線條即可輸入下一條線",
            'almost_done' : '所有的邊長都輸入完成後，按下 enter 進入下一步',
        }[self.guide_state]


    def undo(self):
        line = self._selected_line
        if line.text == 'NA':
            self.goto_previous_screen()
        else:
            line.text = line.text[0:-1]
            self.guide_state = 'typing'
            if line.text == '':
                line.text = 'NA'
                self.guide_text = 'typingNA'
        self.upload_to_manager(**{self.measurements : self.measured_lengths})


    def on_leave(self):
        self.update_routine.cancel()
        for line in list(self._line_segments.values()) + self._vertex_label:
            self.remove_widget(line)


    def compute_grid_mm(self):

        def _locate_p3(d12, d23, d13):
            #設 P1 為 (0, 0), P2 為 (d12, 0)，算出 P3 的座標            
            x = (d23**2 - d13**2 - d12**2) / (-2 * d12)
            y = -(d13 ** 2 - x ** 2) ** 0.5
            return [x, y]

        def locate_p3(p1, p2, d13, d23):
            p1, p2 = [np.array(it) for it in [p1, p2]]
            # p3 被假定落在 p1 p2 向量的左轉側
            p3_to_p1p2 = _locate_p3(norm(p2 - p1), d23, d13)
            p3_complex_p1p2 = p3_to_p1p2[0] + 1j * p3_to_p1p2[1]
            p1p2_unit = (p2 - p1) / norm(p2 - p1)
            p1p2_unit_complex = p1p2_unit[0] + 1j * p1p2_unit[1]
            p1_complex = p1[0] + 1j * p1[1]
            p3_complex = p1_complex + p1p2_unit_complex * p3_complex_p1p2
            return [p3_complex.real, p3_complex.imag]

        # 簡化變數名稱
        row_num, col_num = self._row_num, self._col_num

        # 線長函數
        def length(row1, col1, row2, col2):
            id = self._line_segment_id(row1, col1, row2, col2)
            line = self._line_segments[id]
            return float(line.text)

        # 準備節點座標
        grid = Grid(shape=(row_num, col_num))
        def node(row, col):
            return grid.node(row, col)

        node(0, 0).xy = [0, 0]
        node(1, 0).xy = [0, length(0,0,1,0)]

        # 計算 row 0 和 row 1 的節點
        for col in range(col_num - 1):
            # 這邊用 p_row_col 表示節點
            p00 = node(0, col).xy
            p10 = node(1, col).xy

            # 這邊用 d_row_col_dr_dc 表示是哪兩個點之間的距離
            # 同列的下一個節點
            d00_01 = length(0, col, 0, col + 1)
            d10_01 = length(1, col, 0, col + 1)
            p01 = locate_p3(p00, p10, d00_01, d10_01)
            node(0, col+1).xy = p01

            # 下一列的下一個節點
            d10_11 = length(1, col    , 1, col + 1)
            d01_11 = length(0, col + 1, 1, col + 1)
            p11 = locate_p3(p01, p10, d01_11, d10_11)
            node(1, col+1).xy = p11

        # 如果未來要支援更大的網格勢必要在此撰寫計算其它 row 的程式
        # 現在沒有要做先跳過
        if row_num > 2:
            raise NotImplementedError('More then 2 rows are not handled yet')

        # 至此已經獲得了所有節點座標
        # 接下來可以看要不要去做旋轉

        return grid


    def on_press_enter(self):

        # 檢查各邊是否都已輸入
        ok = False
        self._error_count = 0
        for line in self._line_segments.values():
            if not self.is_legal_length(line.text):
                line.state = 'error'
                self._error_count += 1

        if self._error_count > 0:
            self.guide_state = 'error_found'
            return

        # 所有的邊長都已經輸入才會抵達這裡
        grid_mm = self.compute_grid_mm()
        self.upload_to_manager(**{self.grid_out : grid_mm.griddata})
        self.goto_next_screen()



class VerifyDiagnalScreen(GuideScreen):

    display_grid = StringProperty("display_grid")
    verify_grid = StringProperty("verify_grid")

    def on_enter(self):
        # 準備螢幕座標 (顯示用) 以及真實座標 (計算長度用)
        grid_mm = self.load_from_manager(self.verify_grid)
        grid_pixel = self.load_from_manager(self.display_grid)

        grid_mm = Grid(**grid_mm)
        grid_pixel = Grid(**grid_pixel)

        row_num, col_num = grid_pixel.shape

        def coord_mm(row, col):
            return np.array(grid_mm.node(row, col).xy)

        def coord_pixel(row, col):
            return np.array(grid_pixel.node(row, col).xy)

        # 算出所有 (先前沒測量的) 對角線
        self._diagnals = []
        for col in range(col_num - 1):
            p00 = coord_mm(0, col)
            p11 = coord_mm(1, col+1)
            diagnal_length = norm(p11 - p00)

            # 產生 LineSegment 物件
            pix00 = coord_pixel(0, col)
            pix11 = coord_pixel(1, col + 1)
            diagnal = LineSegment(points=[pix00, pix11], text=str(round(diagnal_length,2)), state='selected')
            self.add_widget(diagnal)        
            self._diagnals.append(diagnal)

        if row_num > 2:
            raise NotImplementedError('More then 2 rows are not handled yet')


    def on_leave(self):
        for w in self._diagnals:
            self.remove_widget(w)

    def on_press_enter(self):
        self.goto_next_screen()


from kivy.lang import Builder
Builder.load_string("""


<VertexLabel>:
    size_hint: None, None
    size: self.texture_size

<LineSegment>:

    background_color: 0, .1, 0, 1.
    on_state: root.render()
    on_text: length_label.core_text = self.text

    ColorLabel:
        id: length_label
        size_hint: None, None
        size: self.texture_size

        on_text_color:  self._render()
        on_core_text: self._render()

        canvas.before:
            Color:
                rgba: root.background_color
            Rectangle:
                pos: self.pos
                size: self.size

<MeasureGridScreen>:
    anchor_x: 'right'
    anchor_y: 'bottom'
    padding: 300
    background: 0, .1, 0
    cursor: 'tiny cross'
    guide: "將游標靠近任一條線以選擇之，接著在鍵盤上輸入其長度 (mm)\\n輸入完成時直接將游標靠近其它線條即可輸入下一條線"


<VerifyDiagnalScreen>:
    cursor: 'hidden'
    background: 0, .1, 0
    anchor_x: 'right'
    anchor_y: 'top'
    padding: 300
    guide: "測量畫面中的線條長度以驗證準確度"

""")