from kivy.properties import NumericProperty, ListProperty, StringProperty, ColorProperty, OptionProperty, BooleanProperty
from kivy.graphics import Line, Color
from kivy.clock import Clock, mainthread

from kivyguidescreen import GuideScreen, GuideScreenVariable
from kivyguidescreen.widgets.grideditor import Grid

import cv2
import numpy as np
from kivyguidescreen.utils.armath import PerspectiveTransform


class VerifyArucoScreen(GuideScreen):

    tracker2d_source = StringProperty()
    tracker_height = NumericProperty(0)

    lens_center_xyz = GuideScreenVariable()
    table_points_pixel = GuideScreenVariable()
    table_points_mm = GuideScreenVariable()

    paused = BooleanProperty(False)

    def on_enter(self):
        # 建立桌面座標到像素的轉換
        table_points_pixel = self.table_points_pixel.read().coords
        table_points_mm = self.table_points_mm.read().coords
        self._xy_to_uv_transform = PerspectiveTransform(src_points=table_points_mm, dst_points=table_points_pixel)

        # 取得鏡心
        self._lens_center_xyz = self.lens_center_xyz.read()

        # 固定索取 aruco 數據
        self._routine = Clock.schedule_interval(self._retrieve_aruco, 1/30)


    def xyz_to_uv(self, xyz):
        cx, cy, cz = self._lens_center_xyz
        hx, hy, hz = xyz
        head_xy = hx, hy
        
        dxy_per_z = np.array([hx-cx, hy-cy]) / (cz-hz)
        tail_xy = np.array(head_xy) + dxy_per_z * hz
        uv = self._xy_to_uv_transform.apply(tail_xy)
        
        return uv


    def on_leave(self):
        if self._routine:
            self._routine.cancel()
            self._routine = None


    def _retrieve_aruco(self, dt):
        if self.paused:
            return

        self.socketio_client.emit(event=self.tracker2d_source.lower(), data='', namespace=None, callback=self._on_receive_aruco)

    def on_paused(self, caller, value):
        if not self.paused:
            self.socketio_client.emit(
                event="set_config",
                data=dict(
                    path=self.tracker2d_source.lower(),
                    config={'compensate_to' : {'0':self._last_pose}}
                    ),
                namespace=None)


    def on_press_space(self):
        self.paused = not self.paused


    @mainthread
    def _on_receive_aruco(self, message):
        self.guide = '檢查投影輪廓是否正確框住校正器'
        corners = message['corners']
        canvas = self.canvas.after
        canvas.clear()
        
        def draw_line(xy_points, z=self.tracker_height, close=False):
            uvs = [self.xyz_to_uv([*xy, z]).tolist() for xy in xy_points]
            if close:
                uvs = uvs + [uvs[0]]
            canvas.add(Line(points=sum(uvs, [])))

        # 畫出參考點
        canvas.add(Color(1, 1, 0))
        p1, p2, p4, p3 = Grid(**self.table_points_mm.read()).coords()
        draw_line(xy_points = [p1, p2, p3, p4], z=0, close=True)

        # 畫出校正器外框
        canvas.add(Color(1, 1, 1))
        for contour in corners.values():
            draw_line(xy_points=contour, close=True)

        # 畫出位置補償後的中心點
        canvas.add(Color(1, 0, 0))
        if 'pose_ue4' in message and '0' in message['pose_ue4']:
            pose_ue4 = message['pose_ue4']['0']
            yc, xc, _ =  pose_ue4['location']
            _, _, yaw = pose_ue4['rotation']

            rad_yaw = -np.deg2rad(yaw)
            cos, sin = np.cos(rad_yaw), np.sin(rad_yaw)
            cen = np.array([xc, yc])
            hvec = np.array([cos, sin])
            vvec = np.array([-sin, cos])
            r = 10
            draw_line(xy_points=[cen-20*hvec, cen+20*hvec])
            draw_line(xy_points=[cen-15*hvec+10*vvec, cen-15*hvec-10*vvec])
            draw_line(xy_points=[cen+15*hvec+10*vvec, cen+15*hvec-10*vvec])

            # 把當前位置記下來隨時準備重設 compensation
            self._last_pose = dict(pos=[yc, xc], yaw=yaw)


    def on_press_enter(self):
        self.goto_next_screen()



class VerifyArucoScreenOld(GuideScreen):

    aruco_line_color = ColorProperty([1, 1, 0])

    tracker2d_source = StringProperty()
    calibrator_height = NumericProperty(0)
    sense_area_size = ListProperty([800, 450])
    sense_area_center = ListProperty([0, 0])

    # 用來建立桌面座標到像素的轉換
    table_corners_pixel = StringProperty('table_corners_pixel')
    table_corners_mm = StringProperty('table_corners_mm')

    # 用來算出鏡心在桌面座標的位置
    lens_center_xyz = StringProperty('lens_center_xyz')
    guage_center = StringProperty('guage_center')
    guage_angle = StringProperty('guage_angle')
    guage_height = NumericProperty(27)

    paused = BooleanProperty(False)

    def on_enter(self):
        # 建立桌面座標到像素的轉換
        table_corners_pixel = Grid(**self.load_from_manager(self.table_corners_pixel)).coords(dtype=np.float32)
        table_corners_mm =  Grid(**self.load_from_manager(self.table_corners_mm)).coords(dtype=np.float32)
        self._xy_to_uv_transform = PerspectiveTransform(src_points=table_corners_mm, dst_points=table_corners_pixel)

        # 計算鏡心要用的變數
        cx, cy, cz = (np.array(self.load_from_manager(self.lens_center_xyz)) * 10).tolist()
        gy, gx, _ = self.load_from_manager(self.guage_center)
        ang = np.deg2rad(self.load_from_manager(self.guage_angle))
        sin, cos = np.sin(ang), np.cos(ang)

        # 計算鏡心
        lenz = cz + self.guage_height
        lenx = gx + cx * cos + cy * sin
        leny = gy - cx * sin + cy * cos
        self._lens_center = [lenx, leny, lenz]

        # 固定索取 aruco 數據
        self._routine = Clock.schedule_interval(self._retrieve_aruco, 1/30)


    def xyz_to_uv(self, xyz):
        cx, cy, cz = self._lens_center
        hx, hy, hz = xyz
        head_xy = hx, hy
        
        dxy_per_z = np.array([hx-cx, hy-cy]) / (cz-hz)
        tail_xy = np.array(head_xy) + dxy_per_z * hz
        uv = self._xy_to_uv_transform.apply(tail_xy)
        
        return uv


    def on_leave(self):
        if self._routine:
            self._routine.cancel()
            self._routine = None


    def _retrieve_aruco(self, dt):
        if self.paused:
            return

        self.socketio_client.emit(event=self.tracker2d_source.lower(), data='', namespace=None, callback=self._on_receive_aruco)

    def on_paused(self, caller, value):
        if not self.paused:
            self.socketio_client.emit(
                event="set_config",
                data=dict(
                    path=self.tracker2d_source.lower(),
                    config={'compensate_to' : {'0':self._last_pose}}
                    ),
                namespace=None)


    def on_press_space(self):
        self.paused = not self.paused


    @mainthread
    def _on_receive_aruco(self, message):
        self.guide = '檢查投影輪廓是否正確框住校正器'
        corners = message['corners']
        canvas = self.canvas.after
        canvas.clear()
        
        def draw_line(xy_points, z=self.calibrator_height, close=False):
            uvs = [self.xyz_to_uv([*xy, z]).tolist() for xy in xy_points]
            if close:
                uvs = uvs + [uvs[0]]
            canvas.add(Line(points=sum(uvs, [])))

        # 畫出感應區
        canvas.add(Color(1, 0, 0))
        tx, ty = self.sense_area_center
        w, h = self.sense_area_size
        draw_line(xy_points = [[-w/2 + tx, -h/2 + ty], [w/2 + tx, -h/2 + ty], [w/2 + tx, h/2 + ty], [-w/2 + tx, h/2 + ty]], z=0, close=True)

        # 畫出桌面
        canvas.add(Color(1, 1, 0))
        p1, p2, p4, p3 = Grid(**self.load_from_manager(self.table_corners_mm)).coords()
        draw_line(xy_points = [p1, p2, p3, p4], z=0, close=True)

        # 畫出校正器外框
        canvas.add(Color(1, 1, 1))
        for contour in corners.values():
            draw_line(xy_points=contour, close=True)

        # 畫出位置補償後的中心點
        canvas.add(Color(1, 0, 0))
        if 'pose_ue4' in message and '0' in message['pose_ue4']:
            pose_ue4 = message['pose_ue4']['0']
            yc, xc, _ =  pose_ue4['location']
            _, _, yaw = pose_ue4['rotation']

            rad_yaw = -np.deg2rad(yaw)
            cos, sin = np.cos(rad_yaw), np.sin(rad_yaw)
            cen = np.array([xc, yc])
            hvec = np.array([cos, sin])
            vvec = np.array([-sin, cos])
            r = 10
            draw_line(xy_points=[cen-20*hvec, cen+20*hvec])
            draw_line(xy_points=[cen-15*hvec+10*vvec, cen-15*hvec-10*vvec])
            draw_line(xy_points=[cen+15*hvec+10*vvec, cen+15*hvec-10*vvec])

            # 把當前位置記下來隨時準備重設 compensation
            self._last_pose = dict(pos=[yc, xc], yaw=yaw)


    def on_press_enter(self):
        self.goto_next_screen()




from kivy.lang import Builder
Builder.load_string("""


<VerifyArucoScreen>:

    switch_monitor_by_digitkey: True
    cursor: 'hidden'
    background: .0, .1, .3

    guide: "連線中..."

""")