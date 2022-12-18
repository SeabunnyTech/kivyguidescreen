import numpy as np
import cv2
from kivy.graphics import Line, Color, Point, InstructionGroup
from kivy.clock import Clock
from kivy.core.window import Window

from kivyguidescreen import GuideScreen, GuideScreenManager, GuideScreenVariable
from kivy.properties import StringProperty, DictProperty, NumericProperty

from kivyguidescreen.utils import armath




class VarifyElevatedQuadScreen(GuideScreen):

    elevation_mm = NumericProperty(120)
    table_quad_mm = GuideScreenVariable()
    table_quad_pixel = GuideScreenVariable()
    elevated_quad_pixel = GuideScreenVariable()

    lens_center_xyz = GuideScreenVariable()

    def _prepare_tansforms(self):
        from kivyguidescreen.utils.armath import PerspectiveTransform
        planar_uvs = self.table_quad_pixel.read().coords
        planar_xys = self.table_quad_mm.read().coords

        # planar_uvs 會持續改變所以 PerspectiveTransform 無法預先產生
        self.uv_to_xy_transform = PerspectiveTransform(src_points=planar_uvs, dst_points=planar_xys)
        self.xy_to_uv_transform = PerspectiveTransform(src_points=planar_xys, dst_points=planar_uvs)

    def to_xy(self, uvs):
        return self.uv_to_xy_transform.apply(uvs)

    def to_uv(self, xys):
        return self.xy_to_uv_transform.apply(xys)


    def on_enter(self):
        self._prepare_tansforms()
        self._lens_center_xyz = self.compute_center_of_lens()
        
        self._routine = Clock.schedule_interval(self._draw_pointer, 1/30)


    def on_press_enter(self):
        self.goto_next_screen()
        self.lens_center_xyz.write(self._lens_center_xyz)


    def on_leave(self):
        if self._routine:
            self._routine.cancel()
            self._routine = None


    def _draw_pointer(self, *args):
        f32 = np.float32

        # 先找出尖點的 xyz
        cursor_x, cursor_y = self.to_xy(self.subpixel_cursor)
        pointer_xyz = f32([cursor_x, cursor_y, self.elevation_mm])

        # 計算從鏡心出發的射線通過尖點後在桌面的落點
        lens_center_xyz = f32(self._lens_center_xyz)
        dxdy_per_z = (lens_center_xyz - pointer_xyz) / (lens_center_xyz[2] - pointer_xyz[2])
        landing_xy = (pointer_xyz - self.elevation_mm * dxdy_per_z)[:2]

        # 畫出投射點        
        canvas = self.canvas.after
        canvas.clear()
        r = 10
        u, v = landing_uv = self.to_uv(landing_xy)
        self.canvas.after.add(Line(points=[u-r, v, u+r, v], width=0.5))
        self.canvas.after.add(Line(points=[u, v-r, u, v+r], width=0.5))


    def compute_center_of_lens(self):

        elevated_uvs = self.elevated_quad_pixel.read().coords
        elevated_xys = self.table_quad_mm.read().coords

        tails_xys = self.to_xy(elevated_uvs)
        heads_xy = [np.array([xy]).reshape(2) for xy in elevated_xys]
        heads_z = self.elevation_mm

        '''
        generating relation matrix
        [[1, 0, ax]
         [0, 1, ay]] * [x, y, z].T = [tx, ty].T
        where ax, ay = (tail - head) / headtop_height
        tx, ty = tail
        '''
        A, b = [], []
        for idx in range(len(elevated_uvs)):
            ax, ay = (tails_xys[idx] - heads_xy[idx]) / float(heads_z)
            arr = np.array([[1, 0, ax], [0, 1, ay]])
            tx, ty = tails_xys[idx]
            A.append(arr)
            b.append([tx, ty])

        # assembly all the points
        A = np.vstack(A)
        b = np.hstack(b)
        
        lens_center_xyz = np.linalg.lstsq(A, b, rcond=None)[0].tolist()

        return [float(c) for c in lens_center_xyz]




class ReportProjectorParameterScreen(GuideScreen):

    lens_center_xyz = StringProperty('lens_center_xyz')

    projector_id = StringProperty('table')
    projector_parameters = DictProperty()

    state_guide = StringProperty('')


    def undo(self):
        self.goto_previous_screen()


    def draw_crosses(self, projector_parameters, color):
        self.canvas.after.add(Color(*color))
        r = 50
        points = self.load_from_manager('planar_points') + self.load_from_manager('peak_points')
        points = [p['xyz'] for p in points]
        p2d = armath.reproject(points, projector_parameters)
        for u,v in p2d:
            self.canvas.after.add(Line(points=[u-r, v, u+r, v], width=0.5))
            self.canvas.after.add(Line(points=[u, v-r, u, v+r], width=0.5))


    def on_enter(self):
        self.canvas.after.clear()
        self.projector_parameters =self.solve_projector_heading()
        self.state_guide = '\n按下空白鍵將校正檔傳送至伺服器儲存為 ' + self.projector_id + '.json\n'


    def solve_projector_heading(self):
        gauge_corners = self.load_from_manager('planar_points')
        projector_parameters = armath.solve_projector_heading(
            lens_center_xyz  = self.load_from_manager(self.lens_center_xyz),    # 鏡心座標的單位是 cm
            table_corners_xy = [it['xyz'][:2] for it in gauge_corners],
            table_corners_uv =  [it['uv'] for it in gauge_corners],
            projector_resolution = self.load_from_manager('windowsize')
        )
        self.draw_crosses(projector_parameters, [1, 0, 0])
        
        ############ try to improve result with opencv built-in calibrateCamera
        '''
        pts = self.load_from_manager('planar_points') + self.load_from_manager('peak_points')
        p2d = np.array([[it['uv'] for it in pts]], dtype=np.float32)
        p3d = np.array([[it['xyz'] for it in pts]], dtype=np.float32)

        cMat = armath.opencv_camera_matrix_from_report(projector_parameters)
        retval, cameraMatrix, distCoeffs, rvecs, tvecs = cv2.calibrateCamera(
            objectPoints=p3d,
            imagePoints=p2d,
            imageSize=(1920, 1080),
            cameraMatrix=cMat,
            distCoeffs=(0,0,0), 
            flags=cv2.CALIB_USE_INTRINSIC_GUESS+cv2.CALIB_FIX_ASPECT_RATIO)

        focal_length = cameraMatrix[0][0]
        dst, jacobian = cv2.Rodrigues(rvecs[0])
        #print(distCoeffs)
        parameters = dict(
            #lens_center=np.array([-46.73546127490675, -43.05294305385354, 157.74856569299684]),
            lens_center=projector_parameters['lens_center'],
            #lens_center=-tvecs[0].reshape(-1),
            forward=-dst[2],
            right=-dst[0],
            up=-dst[1],
            fov=focal_length / 960,
            x_offset=(cameraMatrix[0][2] - 960) / 960,
            y_offset=(cameraMatrix[1][2] - 540) / 960,
            resolution=self.load_from_manager('windowsize')
        )
        self.draw_crosses(parameters, [0, 0, 1])

        parameters = armath.unrealize(parameters)

        for item in parameters.items():
            print(item)
        '''
        ############

        projector_parameters = armath.unrealize(projector_parameters)        
        projector_parameters['lens_center'][2]
        projector_parameters['id'] = self.projector_id
        projector_parameters['guage_center'] = self.load_from_manager('guage_center')
        projector_parameters['guage_angle'] = self.load_from_manager('guage_angle')

        return projector_parameters


    def on_press_space(self):
        self.state_guide = '\n傳送中 ...\n'
        Clock.schedule_once(self.upload_projector_parameters, 0.1)


    def upload_projector_parameters(self, dt):
        self.socketio_client.emit(event='jsonhub.save', data=self.projector_parameters, namespace=None, callback=self.on_done_uploading)


    def on_done_uploading(self, *args):
        self.state_guide = '\n已將校正檔傳送至伺服器儲存為 ' + self.projector_id + '.json\n'


    def on_press_enter(self):
        self.upload_to_manager(projector_parameters=self.projector_parameters)
        self.goto_next_screen()


    def on_state_guide(self, *args):
        self.update_guide()


    def on_projector_parameters(self, *args):
        self.update_guide()


    def update_guide(self, *arg):
        guide = ''

        for it in self.projector_parameters.items():
            guide += str(it[0]) + ': ' + str(it[1]) + '\n'

        guide += self.state_guide

        self.guide = guide




from kivy.lang import Builder
Builder.load_string("""

<VarifyElevatedQuadScreen>:
    cursor: 'tiny cross'
    guide: "任意移動游標，檢查它是否與抬升 " + str(self.elevation_mm) + " mm 後的位置是否相符"

<ReportProjectorParameterScreen>:
    cursor: 'hidden'
    padding: 100
    anchor_y: 'bottom'
    background: {colors.Y}

""".format(colors=GuideScreenManager.colors))

