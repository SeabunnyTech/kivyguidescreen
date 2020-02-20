import cv2
import numpy as np
from numpy.linalg import norm
from scipy.optimize import fsolve



class PerspectiveTransform():

    def __init__(self, matrix):
        self.matrix = matrix


    def apply(self, xy):
        
        pts = np.float32(xy).reshape(1, -1, 2)
        transform = np.float32(self.matrix)

        ret = cv2.perspectiveTransform(pts, transform).reshape(-1, 2)
        if ret.size == 2:
            ret = ret.reshape(2)
        return ret
        


def find_homography(srcPoints, dstPoints):
    mat, mask = cv2.findHomography(
        srcPoints = np.array(srcPoints),
        dstPoints = np.array(dstPoints),
    )
    return mat


def sort_table_corners(corners):
    mu, mv = 0, 0
    for u, v in corners:
        mu, mv = mu + u/4, mv + v/4

    sorted_corners_uv = [None] * 4

    for corner in corners:
        index = 0
        u, v = corner
        if u <= mu and v > mv:
            index = 0
        if u <= mu and v <= mv:
            index = 1
        if u > mu and v <= mv:
            index = 2
        if u > mu and v > mv:
            index = 3

        sorted_corners_uv[index] = corner

    # change to cross implementation if this goes wrong
    assert None not in sorted_corners_uv

    return sorted_corners_uv


def sovle_projector_heading(\
    lens_center_xyz,
    table_corners_xy,
    table_corners_uv):
    
    '''
    變數名稱規範:
        T: Table, 位在桌面上的點
        V: Virtual Screen 在虛擬螢幕上的點, 虛擬螢幕 Virtual Screen 是一個過桌面座標原點且垂直於投影機光軸的平面

        p: positive 最大值
        c: 中央值
        n: negtive  最小值

        _uv  代表是螢幕座標的後綴，不寫時就是 xyz 座標
        
        最前面的小寫 t 代表投影到桌面的點
        最前面的小寫 v 代表投射到虛擬平面的點
        
    根據前述邏輯定義的頂點名稱:

        桌面四角 Tnn, Tpn, Tpp, Tnp = [ [-48, -36, 0], [48, -36, 0], [48, 36, 0], [-48, 36, 0] ]
        螢幕四角 Vnn_uv, Vpn_uv, Vpp_uv, Vnp_uv = [ [0, 0], [1023, 0], [1023, 767], [0, 767] ]

        桌面中心 Tcc = [0, 0, 0]
        螢幕中心 Vcc_uv  = [0, 0]

    特殊變數名:

        N: 虛擬螢幕的法向量
        P: 投影機鏡心座標
        
        Xp, Yp, Zp 是投影機的三軸, Zp 為光軸, 也是投射方向

        沿用名稱規範投影機投在特殊平面上的位置為 vP
    '''
    
    # 投影機鏡心座標
    P = np.array(lens_center_xyz)

    # 桌面角落座標
    table_corners_xy = np.array(sort_table_corners(table_corners_xy))
    Tnp, Tnn, Tpn, Tpp = np.array([[x, y, 0] for x, y in table_corners_xy])

    # 桌面角落的螢幕座標
    table_corners_uv = np.array(sort_table_corners(table_corners_uv))
    Tnp_uv, Tnn_uv, Tpn_uv, Tpp_uv = [np.array(uv) for uv in table_corners_uv]

    screen_to_table_transform, mask = cv2.findHomography(
        srcPoints = table_corners_uv,
        dstPoints = table_corners_xy,
    )

    def to_xy(uv):
        pts = np.float32(uv).reshape(1, -1, 2)
        #screen_to_table_transform = np.float32(self.settings.screen_to_table_transform)

        ret = cv2.perspectiveTransform(pts, screen_to_table_transform).reshape(-1, 2)
        if ret.size == 2:
            ret = ret.reshape(2)
        return ret


    ####### 計算四邊長上下邊的差除以和以及左右邊的差除以和##########
    
    def nddns(vec1, vec2):
        # norm difference divided by norm sum
        len1, len2 = norm(vec1), norm(vec2)
        return (len1- len2) / (len1 + len2)
    
    # 計算桌面 高 度在螢幕 左右 的差除以和
    #            (pp    -  pn)    (np    -  nn)
    dh_x = nddns(Tpp_uv - Tpn_uv, Tnp_uv - Tnn_uv)

    # 計算桌面 寬 度在螢幕 上下 的差除以和
    #            (pp    -  np)     (pn    -  nn)
    dw_y = nddns(Tpp_uv - Tnp_uv, Tpn_uv - Tnn_uv)
    
    ################################################################

    def project_to_virtual_screen(table_xyz, N):
        # 由 Pi = P + si(Vi - P) 以及 Pi * N = 0 出發可以得知 0 = P * N + si(Vi-P) * N
        # 於是就可以導出 si 並推出 Pi
        V, N = [np.array(val) for val in [table_xyz, N] ]
        if not np.allclose(V, P):
            return P + ( P.dot(N) / (P - V).dot(N) ) * (V - P)
        else:
            # projectee = P - sN
            # (P - sN).dot(N) = 0, => s = P*N / N*N => P-sN = P - (P*N / N*N) N
            return P - ((P.dot(N) / N.dot(N))) * N

    def project_to_virtual_screen_from_uv(uv, N):
        
        x, y = to_xy(uv)
        return project_to_virtual_screen([x, y, 0], N)

    def rect_distortion(normal_correction):
        dx, dy = normal_correction
        N = np.array([dx, dy, 1])

        # 計算給定投影機鏡心 P 以及虛擬平面法向量 N 以後
        # 桌面四角在投影面上的投影點形成的四邊形它們的 3D 座標
        vTnp, vTnn, vTpn, vTpp = [project_to_virtual_screen(V, N) for V in [Tnp, Tnn, Tpn, Tpp]]

        # 計算設定投影面後導出來的邊長差和比
        computed_dh_x = nddns(vTpp - vTpn, vTnp - vTnn)
        computed_dw_y = nddns(vTpp - vTnp, vTpn - vTnn)
        
        return computed_dh_x - dh_x, computed_dw_y - dw_y

    # 尋找能讓四邊看起來最像平行四邊形的 Virtual Sreen 法向量 N, 
    dx, dy = fsolve(rect_distortion, x0=(0,0))
    Zp = -np.float32([dx, dy, 1])

    # 投影區域的底邊向量平行 x 軸
    Vpn = project_to_virtual_screen_from_uv([1023, 0], N=Zp)
    Vnn = project_to_virtual_screen_from_uv([0, 0], N=Zp)
    Xp = Vpn - Vnn

    # Unreal 使用左手座標系, y = x cross z
    Yp = np.cross(Xp, Zp)
    Xp, Yp, Zp = [vec / norm(vec) for vec in [Xp, Yp, Zp]]

    ####################################### Rotation Axies
    front, right, up = Zp, Xp, Yp

    ############### find fov
    vP = project_to_virtual_screen(P, N=Zp)
    len_P_vP = norm(P - vP)
    fov = len_P_vP / norm((Vpn - Vnn) / 2)

    ############### find cx, cy        
    Vcc = project_to_virtual_screen_from_uv([1023/2, 767/2], N=Zp)
    cxcy = (vP - Vcc) / len_P_vP
    cx, cy = cxcy.dot(Xp), cxcy.dot(Yp)
    cx, cy = cx * fov , cy * fov

    ################ Unreal-ize and de-numpy (to make variables json-serializable)
    P = P * 10
    vecs = dict(
        lens_center=P,
        front=front,
        right=right,
        up=up
    )

    for k in vecs:
        v = vecs[k]
        new_vec = v[1], v[0], v[2]
        vecs[k] = [float(v) for v in new_vec]

    vars = dict(
        fov=fov,
        x_offset=cx,
        y_offset=cy,
    )
    
    for v in vars:
        vars[v] = float(vars[v])
    
    ################# output
    report = {}
    report.update(vars)
    report.update(vecs)

    return report