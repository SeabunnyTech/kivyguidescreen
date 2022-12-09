
import cv2
import numpy as np

from kivy.clock import Clock
from kivy.graphics import Line, Color, Rectangle, InstructionGroup
from kivy.properties import OptionProperty, NumericProperty, StringProperty
from kivy.core.window import Window
from kivy.utils import QueryDict

from kivyguidescreen import GuideScreen, GuideScreenManager
from kivyguidescreen.utils.armath import PerspectiveTransform



class AutoGuageScreen(GuideScreen):

    mode = OptionProperty('welcome', options=['welcome', 'error', 'testsensor', 'th_black', 'th_white', 'autorun'])

    sensor_xyzs = [
        [ 22.5,  14,    0],
        [ 22.5, -14,    0],
        [   13,  -3, 11.5],
        [  -13,  -3, 11.5],
        [-22.5,  14,    0],        
        [-22.5, -14,    0],
    ]
    '''
    sensor_xyzs = [
        [ 22,  11,  0], #pp
        [ 13,   3, 12],
        [ 22, -11,  0], #pn
        [-13,   3, 12],
        [-22, -11,  0], #nn
        [-22,  11,  0]  #np
    ]
    '''

    planar_indices = [0,1,5, 4]
    peak_indices = [2, 3]

    def __init__(self, light_settle_time=0.2, **kw):
        super().__init__(**kw)
        self.serialport = None
        self.settle_time = light_settle_time
        with self.canvas.after:
            Color(1, 1, 1)
            self.testblock_instructions = InstructionGroup()
            self.whiteband_instructions = InstructionGroup()
            Color(1, 1, 0)
            self.yellow_cross_instructions = InstructionGroup()


    def on_enter(self):
        import serial
        ser = self.serialport = serial.Serial(timeout=self.settle_time)
        ser.baudrate = 9600
        ser.port = self.arduino_guage_port = self.load_from_manager('arduino_guage_port')
        self._routine = None
        self.windowsize = self.load_from_manager('windowsize')
        try:
            ser.open()
            self.mode = 'welcome'
            self.guide = '正在連接 {port} ....'.format(port=self.serialport.port)
            Clock.schedule_once(self._on_serial_open, 2)
        except serial.serialutil.SerialException:
            self.guide = '無法連接 {port}。按下 Enter 跳至過自動對準\n\n或按下 Backspace 回到上一頁選擇連接埠'.format(port=self.serialport.port)
            self.mode = 'error'

    def _on_serial_open(self, dt):
        self._routine = Clock.schedule_interval(self.draw_white_block, 1/60)
        self.mode = 'testsensor'


    def on_leave(self):
        if self._routine:
            self._routine.cancel()
            self._routine = None
        self.serialport.close()


    def on_press_enter(self):
        self.goto_next_screen()


    def on_press_space(self):
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
        Clock.schedule_once(self.capture_and_schedule_next_draw, self.settle_time)


    def update_vars(self):
        planar_points = []
        for idx in self.planar_indices:
            planar_points.append(
                dict(
                    uv=self.sensor_uvs[idx],
                    xyz=self.sensor_xyzs[idx]
                )
            )
        self.upload_to_manager(planar_points=planar_points)
        
        peak_points = []
        for idx in self.peak_indices:
            peak_points.append(
                dict(
                    uv=self.sensor_uvs[idx],
                    xyz=self.sensor_xyzs[idx]
                )
            )
        self.upload_to_manager(peak_points=peak_points)


    def capture_and_schedule_next_draw(self, dt):
        # capture value in current frame
        self.serialport.write(b'\n')
        line = self.serialport.readline().decode()
        values = [int(n) for n in line.split(',')]

        ins = self.whiteband_instructions
        ins.clear()
        
        win_w, win_h = self.windowsize
        wstep, hstep = self.wstep, self.hstep
        
        if self.mode == 'th_black':
            # capture black image value, draw white image
            self.sensor_lower_bounds = values
            ins.add(Rectangle(pos=[0,0], size=self.windowsize))
            self.mode = 'th_white'
        elif self.mode == 'th_white':
            # capture white image values, draw the first horizontal stage
            self.sensor_upperbounds = values
            
            # compute thresholds
            self.sensor_thresholds = []
            for up, lo in zip(self.sensor_upperbounds, self.sensor_lower_bounds):
                self.sensor_thresholds.append((up+lo)/ 2)

            ins.add(Rectangle(pos=[wstep,0], size=[wstep, win_h]))
            self.mode = 'autorun'
        elif self.mode == 'autorun':
            if wstep > 0:
                sensorstates = zip(values, self.sensor_thresholds, self.sensor_expecting_white)
                # intepret the pattern and compute sensor u position (screen x position)
                for index, sensor_state in enumerate(sensorstates):
                    value, threshold, expecting_white = sensor_state
                    is_white = value > threshold
                    if is_white == expecting_white:
                        self.sensor_uvs[index][0] += wstep
                    
                    if is_white:
                        self.sensor_expecting_white[index] = not expecting_white

                wstep = self.wstep = wstep // 2

                if wstep > 0:
                    # draw the next (u-finding) pattern
                    for idx in range(win_w//wstep):
                        if (idx-1) % 4 < 2:
                            ins.add(Rectangle(pos=[idx * wstep,0], size=[wstep, win_h]))
                else:
                    # draw vertical patterns
                    ins.add(Rectangle(pos=[0, hstep], size=[win_w, hstep]))

                    # reset expecting white for vertical operation
                    self.sensor_expecting_white = [True] * 6

            elif hstep > 0:
                # the vertiacal version of the code above
                sensorstates = zip(values, self.sensor_thresholds, self.sensor_expecting_white)
                for index, sensor_state in enumerate(sensorstates):
                    value, threshold, expecting_white = sensor_state
                    is_white = value > threshold
                    if is_white == expecting_white:
                        self.sensor_uvs[index][1] += hstep
                    
                    if is_white:
                        self.sensor_expecting_white[index] = not expecting_white
                hstep = self.hstep = hstep // 2

                if hstep > 0:
                    for idx in range(win_w//hstep):
                        if (idx-1) % 4 < 2:
                            ins.add(Rectangle(pos=[0, idx * hstep], size=[win_w, hstep]))
                else:
                    # 校正完成~~~~ 標示光感測器所在的位置
                    verify_ins = self.yellow_cross_instructions
                    for pt in self.sensor_uvs:
                        x, y = pt
                        verify_ins.add(Line(points=[x, y-20, x, y+20], width=0.5))
                        verify_ins.add(Line(points=[x-20, y, x+20, y], width=0.5))

                    # 進入下一個模式
                    self.update_vars()
                    self.goto_next_screen()

        if self.hstep > 0:
            Clock.schedule_once(self.capture_and_schedule_next_draw, self.settle_time)



    def draw_white_block(self, dt):
        ins = self.testblock_instructions
        ins.clear()
        if self.mode == 'testsensor':
            px, py = Window.mouse_pos
            ins.add(Rectangle(pos=(px-50, py-50), size=(100, 100)))
            self.serialport.write(b'\n')
            line = self.serialport.readline()
            w, h = self.windowsize
            self.guide = '已連接至 {port}。按下空白鍵開始對 {w}x{h} 的投影機進行校正\n或滑動游標來測試個別感應器\n\n'.format(
                port=self.serialport.port,
                w=w,
                h=h,
            ) + line.decode()


    def undo(self):
        if self.mode in ['th_black', 'th_white', 'autorun']:
            self.mode = 'welcome'
            all_ins = [
                self.testblock_instructions,
                self.whiteband_instructions,
                self.yellow_cross_instructions
            ]
            for ins in all_ins:
                ins.clear()
        elif self.mode in ['welcome', 'testsensor', 'error']:
            self.goto_previous_screen()


    





class MoveMarkScreen(GuideScreen):



    def on_enter(self):
        # 讀入所有的參考點
        planar_points = self.load_from_manager('planar_points')
        peak_points = self.load_from_manager('peak_points')

        # 將投影參考點載入到 GridEditor 方便編輯
        planar_uvs = [it['uv'] for it in planar_points]
        peak_uvs = [it['uv'] for it in peak_points]
        self.ids.grideditor.load_grid(coords=planar_uvs + peak_uvs)

        # 準備 peak_points 及 planar_xys 備用
        self.peak_xyzs = [it['xyz'] for it in peak_points]
        self.planar_xys = [it['xyz'][:2] for it in planar_points]

        self.guide = '將滑鼠靠近四角的標記，以左鍵或上下左右鍵對標記位置做微調以符合矩形的桌面\n完成後按 Enter 觀看矩形輔助線'


    def on_press_arrow(self, keyname, dxdy):
        self.ids.grideditor.move_selection(dxdy, scale=0.25)


    @property
    def planar_uvs(self):
        griddata = self.ids.grideditor.griddata
        return griddata['coords'][:4]


    @property
    def peak_uvs(self):
        griddata = self.ids.grideditor.griddata
        return griddata['coords'][4:]


    def on_press_enter(self):

        # update 
        plannar_points = [{'uv':uv, 'xyz':[*xy, 0]} for uv, xy in zip(self.planar_uvs, self.planar_xys)]
        peak_points = [{'uv':uv, 'xyz':xyz} for uv, xyz in zip(self.peak_uvs, self.peak_xyzs)]
        self.upload_to_manager(
            planar_points=plannar_points,
            peak_points=peak_points
        )

        # find lens center
        lens_center_xyz = self.compute_center_of_lens()
        self.upload_to_manager(lens_center_xyz=lens_center_xyz)

        self.goto_next_screen()


    def to_xy(self, uvs):
        from kivyguidescreen.utils.armath import PerspectiveTransform
        planar_uvs = self.planar_uvs
        planar_xys = self.planar_xys

        # planar_uvs 會持續改變所以 PerspectiveTransform 無法預先產生
        pt = PerspectiveTransform(src_points=planar_uvs, dst_points=planar_xys)
        return pt.apply(uvs)


    def compute_center_of_lens(self):

        tails_xy = self.to_xy(self.peak_uvs)
        heads_xy = [np.array([ xyz[:2] ]).reshape(2) for xyz in self.peak_xyzs]
        heads_z = [xyz[2] for xyz in self.peak_xyzs]

        '''
        generating relation matrix
        [[1, 0, ax]
         [0, 1, ay]] * [x, y, z].T = [tx, ty].T
        where ax, ay = (tail - head) / headtop_height
        tx, ty = tail
        '''
        A, b = [], []
        for idx in range(len(self.peak_uvs)):
            ax, ay = (tails_xy[idx] - heads_xy[idx]) / float(heads_z[idx])
            arr = np.array([[1, 0, ax], [0, 1, ay]])
            tx, ty = tails_xy[idx]
            A.append(arr)
            b.append([tx, ty])

        # assembly all the points
        A = np.vstack(A)
        b = np.hstack(b)
        
        lens_center_xyz = np.linalg.lstsq(A, b, rcond=None)[0].tolist()

        return [float(c) for c in lens_center_xyz]
 



class VerifyLensCenterScreen(GuideScreen):

    lines = [
        [[-13, -2.89, 11.5], [-13, 2.89, 11.5]],
        [[13, -2.89, 11.5], [13, 2.89, 11.5]],
        
        [[-22.39, -14, 0], [22.39, -14, 0]],
        [[-22.39, 14, 0], [22.39, 14, 0]],
    ]

    '''
    lines = [
        # upper
        [[-12.5, 0.5, 12], [12.5, 0.5, 12]],
        [[-12.5, -0.5, 12], [12.5, -0.5, 12]],
        
        # planar-horizontal
        [[-23.5,  14.5, 0], [ 23.5,  14.5, 0]],
        [[-23.5, -14.5, 0], [ 23.5, -14.5, 0]],
        
        # planar-vertical
        [[-14.5, 14.5, 0], [-14.5, -14.5, 0]],
        [[ 14.5, 14.5, 0], [ 14.5, -14.5, 0]],
    ]
    '''

    def __init__(self,**kw):
        super().__init__(**kw)
        with self.canvas.after:
            Color(1, 1, 1)
            self.draw_frame_instructions = InstructionGroup()

    def on_enter(self):
        planar_points = self.planar_points = self.load_from_manager('planar_points')

        uvs = [it['uv'] for it in planar_points]
        xys = [it['xyz'][:2] for it in planar_points]
        self._perspective_transform = PerspectiveTransform(src_points=xys, dst_points=uvs)

        self.lens_center_xyz = self.load_from_manager('lens_center_xyz')
        self.draw_frame_instructions.clear()
        for line in self.lines:
            self.draw_line(line)

    def draw_line(self, line):
        u1, v1 = self.xyz_to_uv(line[0])
        u2, v2 = self.xyz_to_uv(line[1])
        ins = self.draw_frame_instructions
        ins.add(Line(points=[u1, v1, u2, v2]))


    def to_uv(self, xys):
        return self._perspective_transform.apply(xys)

    def xyz_to_uv(self, xyz):
        cx, cy, cz = self.lens_center_xyz
        hx, hy, hz = xyz
        head_xy = hx, hy
        
        dxy_per_z = np.array([hx-cx, hy-cy]) / (cz-hz)
        tail_xy = np.array(head_xy) + dxy_per_z * hz
        uv = self.to_uv(tail_xy)
        
        return uv




 

class LocateGuageScreen(GuideScreen):

    """
    警告: 以前寫的 xyz 座標單位是 cm
    """


    table_corners_mm = StringProperty('table_corners_mm')
    table_corners_pixel = StringProperty('table_corners_pixel')
    guage_height = NumericProperty(2.7)

    guage_center = StringProperty('guage_center')
    guage_angle = StringProperty('guage_angle')

    def on_enter(self):

        # 載入 lens center 以及 planar points 以建立校正器座標上的 mm => pixel 轉換
        planar_points = self.planar_points = self.load_from_manager('planar_points')
        uvs = [it['uv'] for it in planar_points]
        xys = [it['xyz'][:2] for it in planar_points]
        self._xy_to_uv_transform = PerspectiveTransform(src_points=xys, dst_points=uvs)
        self.lens_center_xyz = self.load_from_manager('lens_center_xyz')

        # 載入桌面座標以建立桌面的 pixel => mm 轉換
        table_corners_mm = self.load_from_manager(self.table_corners_mm).coords
        table_corners_pixel = self.load_from_manager(self.table_corners_pixel).coords
        self._table_uv_to_xy = PerspectiveTransform(src_points=table_corners_pixel, dst_points=table_corners_mm)

        # 計算原點
        origin_table_xy = self.project_gauge_xy0_to_table_xy([0, 0])

        # 計算 x 單位向量
        x_axis_table_xy = self.project_gauge_xy0_to_table_xy([1, 0])
        x_axis_vec = np.array(x_axis_table_xy) - np.array(origin_table_xy)
        x_unit_vec = (x_axis_vec / np.linalg.norm(x_axis_vec)).tolist()#round(decimals=4)

        # 計算轉角
        guage_angle = -float(np.angle(x_unit_vec[0] + 1j * x_unit_vec[1], deg=True))

        # 上傳轉角以及中心
        ox, oy = origin_table_xy.tolist()
        ue4_origin_table_xy = [oy, ox]
        self.upload_to_manager(**{
            self.guage_center : [*ue4_origin_table_xy, 0],
            self.guage_angle  : guage_angle
        })

        # 接下來把 gauge 座標先除去旋轉，再扣除原點平移就可以變成桌面座標
        self.guide = "校正器中心點位在 " + str(origin_table_xy) + " (單位 mm)\n\n x 方向向量為 " + str(x_unit_vec) + '\n\n確認無誤後按下 enter 繼續'



    def project_gauge_xy0_to_table_xy(self, xy):
        uv = self.xyz_to_uv([*xy, -self.guage_height])
        return self._table_uv_to_xy.apply(uv)


    def xyz_to_uv(self, xyz):
        cx, cy, cz = self.lens_center_xyz
        hx, hy, hz = xyz
        head_xy = hx, hy
        
        dxy_per_z = np.array([hx-cx, hy-cy]) / (cz-hz)
        tail_xy = np.array(head_xy) + dxy_per_z * hz
        uv = self._xy_to_uv_transform.apply(tail_xy)
        
        return uv


    def on_press_enter(self):
        self.goto_next_screen()



from kivy.lang import Builder
Builder.load_string("""

<AutoGuageScreen>:
    switch_monitor_by_digitkey: True
    cursor: 'hidden'
    anchor_y: 'top'
    anchor_x: 'right'
    padding: 100


<MoveMarkScreen>:
    switch_monitor_by_digitkey: True
    anchor_y: 'bottom'
    GridEditor:
        id: grideditor
        draw_line: False
        draw_nodes: True


<VerifyLensCenterScreen>:
    switch_monitor_by_digitkey: True
    cursor: 'hidden'
    anchor_y: 'bottom'
    guide: '檢查投影線是否對準了感測點以確認鏡心位置準確'




""".format(colors=GuideScreenManager.colors))
 