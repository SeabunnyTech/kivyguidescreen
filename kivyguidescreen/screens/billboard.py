import numpy as np
import cv2
from .. import GuideScreenManager, GuideScreen

from kivy.properties import NumericProperty, BooleanProperty, ListProperty, StringProperty, DictProperty
from kivy.graphics import Line, Color, Point, InstructionGroup

from kivy.clock import Clock
from kivy.utils import QueryDict
from kivy.core.window import Window

from ..utils.armath import PerspectiveTransform

class PickQuadCornersScreen(GuideScreen):


    def __init__(self, quadname=None, **kw):

        self.quadname = quadname

        super(PickQuadCornersScreen, self).__init__(**kw)
        self.state.corners = []

        with self.canvas.after:
            Color(rgb=[1, 0, 0])
            self.corner_instructions = InstructionGroup()


    def on_press_enter(self):
        if len(self.state.corners) < 4:
            self.pickcorner()
        else:
            if self.quadname:
                self.upload_to_manaer({self.quadname: self.indexed_corners})
            self.goto_next_screen()


    def on_enter(self):
        self.update()


    def update(self, *args):

        corners = self.state.corners

        if len(corners) < 4:
            self.guide = '請將游標移至四角所在位置並按下 enter 以選擇: {i} / 4'.format(i=len(corners) + 1)
        else:
            self.guide = '完成! 按下 enter 以進入測試畫面'

        self.corner_instructions.clear()

        points = []
        for p in corners:
            points = points + p

        #### add the last edge by repeating the first point
        if len(corners) == 4:
            points = points + corners[0]

        for ins in [ Line(points=points), Point(points=points, pointsize=2) ]:
            self.corner_instructions.add(ins)


    def pickcorner(self):
        u, v = self.manager.subpixel_cursor
        self.state.corners.append([u, v])
        self.update()


    def undo(self, *args):
        if self.state.corners != []:
            corners = self.state.corners.pop()
            self.update()
        else:
            self.goto_previous_screen()


    @property
    def indexed_corners(self):

        corners = self.state.corners
        return {
            'nn' : corners[0],
            'pn' : corners[1],
            'pp' : corners[2],
            'np' : corners[3]
        }
        
        ########### the old good sorting code

        corners = self.state.corners
        assert len(corners) == 4

        mu, mv = 0, 0
        for u, v in corners:
            mu, mv = mu + u/4, mv + v/4

        ret = {}

        for corner in corners:
            index = 0
            u, v = corner
            x_key = 'n' if u <= mu else 'p'
            y_key = 'n' if v <= mv else 'p'
            key = x_key + y_key

            ret[key] = corner

        return ret




class TableHomographyScreen(PickQuadCornersScreen):

    '''
    screen coordination uv
    table coordination xy
    '''

    def __init__(self, table_coords=None, tablesize=None, **kw):
        super().__init__(**kw)

        if (table_coords is None) == (tablesize is None):
            raise ValueError(self.__class__ + ': One and only one parameters in [table_coords, tablesize] should be assigned')

        if table_coords is not None:
            self.table_corners = table_coords
        
        if tablesize is not None:
            w, h = tablesize
            self.table_corners = QueryDict(
                nn = [-w/2, -h/2],
                pn = [ w/2, -h/2],
                pp = [ w/2,  h/2],
                np = [-w/2,  h/2],
            )


    def update(self):
        super().update()
        table_corners = self.table_corners
        num_selected_corners = len(self.state.corners)
        
        if num_selected_corners < 4:
            key = ['nn', 'pn', 'pp', 'np']
            x, y = table_corners[key[num_selected_corners]]
            self.guide = '請將游標對準 ({x}, {y}) 處後按下 enter 以選擇，單位為公分: ({i}/4)'.format(
                i=num_selected_corners + 1,
                x=x,
                y=y,
            )
        else:
            self.guide = '完成! 按下 enter 以進入測試畫面'


    def goto_next_screen(self):
        table_matrices = self.find_homography()
        screen_to_table_matrix = table_matrices.screen_to_table
        table_to_screen_matrix = table_matrices.table_to_screen

        self.upload_to_manager(
            table_corners = self.indexed_corners,
            screen_to_table_matrix=screen_to_table_matrix,
            table_to_screen_matrix=table_to_screen_matrix
        )
        super().goto_next_screen()


    def find_homography(self, *args):
        if len(self.state.corners) < 4:
            raise Exception("Not enough corners provided")

        corners = self.state.corners

        uv_list, xy_list = [], []
        for ck in ['nn', 'np', 'pp', 'pn']:
            uv = self.indexed_corners[ck]
            xy = self.table_corners[ck]
            uv_list.append(uv)
            xy_list.append(xy)

        screen_to_table, mask = cv2.findHomography(
            srcPoints = np.array(uv_list),
            dstPoints = np.array(xy_list),
        )

        table_to_screen, mask = cv2.findHomography(
            srcPoints = np.array(xy_list),
            dstPoints = np.array(uv_list),
        )

        return QueryDict(
            screen_to_table = screen_to_table.tolist(),
            table_to_screen = table_to_screen.tolist()
        )


class VerifyTableHomographyScreen(GuideScreen):

    test_length = NumericProperty(50.0)

    def __init__(self, test_length=50, **kw):
        super().__init__(**kw)

        self.test_length = test_length
        with self.canvas:
            Color(0, 0, 0)
            self.calib_rect = InstructionGroup()


    def on_pre_enter(self):
        
        scale = self.test_length / 2.0
        
        p1 = (1.0 + 1j) * scale
        pts1 = [p1, p1*1j, -p1, -p1*1j, p1]
        p2 = (1.4 + 0.2j) * scale
        pts2 = [p2, p2*1j, -p2, -p2*1j, p2]

        matrix = self.load_from_manager('table_to_screen_matrix')
        xy_to_uv_transform = PerspectiveTransform(matrix)
        
        self.calib_rect.clear()
        for pts in [pts1, pts2]:
            pts = [[p.real, p.imag] for p in pts]
            rect = xy_to_uv_transform.apply(pts)
            rect = Line(points=list(rect.flatten()))
            self.calib_rect.add(rect)


    def on_touch_down(self, *args):
        self.goto_next_screen()


    def on_press_enter(self, *args):
        self.goto_next_screen()


    def undo(self, *args):
        self.goto_previous_screen()





from kivy.lang import Builder
Builder.load_string('''
<PickQuadCornersScreen>:
    numpad_as_arrows: True
    background: {colors.Y}

    
<VerifyTableHomographyScreen>:
    background: {colors.Y}
    guide: '完成! 請確認畫面中的正方形每一邊都的長度都是 ' + str(self.test_length) + ' cm\\n完成後按 enter 繼續'

'''.format(colors=GuideScreenManager.colors))


if __name__ == '__main__':
    gsm = GuideScreenManager()
    
    gsm.add_widget(TableHomographyScreen(name='pickcorner'))
    gsm.add_widget(VerifyTableHomographyScreen(name='verify'))

    from kivy.base import runTouchApp

    try:
        runTouchApp(gsm)
    except:
        import traceback
        traceback.print_exc()
    finally:
        gsm.autosave()