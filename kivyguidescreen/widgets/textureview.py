import numpy as np

from kivy.properties import NumericProperty, ReferenceListProperty, OptionProperty
from kivy.graphics import RenderContext, Rectangle
from kivy.graphics.texture import Texture
from kivy.uix.widget import Widget

from kivy.clock import Clock

grayscale = '''
#version 440
#ifdef GL_ES
    precision highp float;
#endif

/* Outputs from the vertex shader */
varying vec4 frag_color;
varying vec2 tex_coord0;
/* uniform texture samplers */
uniform sampler2D texture0;

void main (void) {
    gl_FragColor = vec4(texture2D(texture0, tex_coord0).rgb, 1.0);
}
'''



fragment_header = '''
#ifdef GL_ES
    precision highp float;
#endif

/* Outputs from the vertex shader */
varying vec4 frag_color;
varying vec2 tex_coord0;

/* uniform texture samplers */
uniform sampler2D texture0;

/* custom input */
uniform float depth_range;
uniform vec2 size;
'''

hsv_func = '''
vec3 HSVtoRGB(vec3 color) {
    float f,p,q,t, hueRound;
    int hueIndex;
    float hue, saturation, v;
    vec3 result;

    /* just for clarity */
    hue = color.r;
    saturation = color.g;
    v = color.b;

    hueRound = floor(hue * 6.0);
    hueIndex = mod(int(hueRound), 6.);
    f = (hue * 6.0) - hueRound;
    p = v * (1.0 - saturation);
    q = v * (1.0 - f*saturation);
    t = v * (1.0 - (1.0 - f)*saturation);

    switch(hueIndex) {
        case 0:
            result = vec3(v,t,p);
        break;
        case 1:
            result = vec3(q,v,p);
        break;
        case 2:
            result = vec3(p,v,t);
        break;
        case 3:
            result = vec3(p,q,v);
        break;
        case 4:
            result = vec3(t,p,v);
        break;
        case 5:
            result = vec3(v,p,q);
        break;
    }
    return result;
}
'''

rgb_kinect = fragment_header + '''
void main (void) {
    float value = texture2D(texture0, tex_coord0).r;
    value = mod(value * depth_range, 1.);
    vec3 col = vec3(0., 0., 0.);
    if ( value <= 0.33 )
        col.r = clamp(value, 0., 0.33) * 3.;
    if ( value <= 0.66 )
        col.g = clamp(value - 0.33, 0., 0.33) * 3.;
    col.b = clamp(value - 0.66, 0., 0.33) * 3.;
    gl_FragColor = vec4(col, 1.);
}
'''

points_kinect = fragment_header + hsv_func + '''
void main (void) {
    // threshold used to reduce the depth (better result)
    const int th = 5;

    // size of a square
    int square = floor(depth_range);

    // number of square on the display
    vec2 count = size / square;

    // current position of the square
    vec2 pos = floor(tex_coord0.xy * count) / count;

    // texture step to pass to another square
    vec2 step = 1 / count;

    // texture step to pass to another pixel
    vec2 pxstep = 1 / size;

    // center of the square
    vec2 center = pos + step / 2.;

    // calculate average of every pixels in the square
    float s = 0, x, y;
    for (x = 0; x < square; x++) {
        for (y = 0; y < square; y++) {
            s += texture2D(texture0, pos + pxstep * vec2(x,y)).r;
        }
    }
    float v = s / (square * square);

    // threshold the value
    float dr = th / 10.;
    v = min(v, dr) / dr;

    // calculate the distance between the center of the square and current pixel
    // display the pixel only if the distance is inside the circle
    float vdist = length(abs(tex_coord0 - center) * size / square);
    float value = 1 - v;
    if ( vdist < value ) {
        vec3 col = HSVtoRGB(vec3(value, 1., 1.));
        gl_FragColor = vec4(col, 1);
    }
}
'''
hsv = fragment_header + hsv_func + '''
void main (void) {
    float value = texture2D(texture0, tex_coord0).r;
    //value = mod(value * depth_range, 1.);
    vec3 col = HSVtoRGB(vec3(value, 1., 1.)) * 0.7;
    gl_FragColor = vec4(col, 1.);
}
'''










class TextureView(Widget):

    shader = OptionProperty('grayscale', options=['grayscale', 'hsv'])
    
    texture_width = NumericProperty(0)
    texture_height = NumericProperty(0)
    texture_size = ReferenceListProperty(texture_width, texture_height)

    colorfmt = OptionProperty('rgb', options=['rgb', 'rgba', 'luminance', 'luminance_alpha', 'bgr', 'bgra'])
    bufferfmt = OptionProperty('ubyte', options=['ubyte', 'ushort', 'uint', 'byte', 'short', 'int', 'float'])

    def __init__(self, texture_size=(100, 100), colorfmt='rgb', bufferfmt='ubyte', **kwargs):

        # init
        super(TextureView, self).__init__(**kwargs)
        self.canvas = RenderContext(use_parent_projection=True)
        self.canvas.shader.fs = eval(self.shader)

        with self.canvas:
            self.rect = Rectangle(pos=self.pos, size=self.size)#, texture=self.texture)

        # load variables
        self.texture_size = texture_size
        self.colorfmt = colorfmt
        self.bufferfmt = bufferfmt

        # init
        self._reallocate_scheduled = False
        self._schedule_texture_reallocation()

        # bind all properties to reallocate texture
        for it in ['colorfmt', 'bufferfmt', 'texture_size', 'texture_width', 'texture_height']:
            self.bind(**{it:self._schedule_texture_reallocation})

        self.register_event_type('on_texture_allocated')



    def _reallocate_texture(self, *args):

        self.texture = Texture.create(
            size=self.texture_size,
            colorfmt=self.colorfmt,
            bufferfmt=self.bufferfmt
        )
        
        self.rect.texture = self.texture
        self._reallocate_scheduled = False
        self.dispatch('on_texture_allocated')


    def _schedule_texture_reallocation(self, *args):
        # do not reallocate multiple times
        if self._reallocate_scheduled:
            return

        if not self._reallocate_scheduled:
            self._reallocate_scheduled = True

        Clock.schedule_once(self._reallocate_texture, 0)


    def on_texture_allocated(self, *args):
        pass


    def on_size(self, *args):
        self.rect.size = self.size


    def on_pos(self, *args):
        self.rect.pos = self.pos
        

    def blit_to_texture(self, byte_arr):
        self.texture.blit_buffer(
            byte_arr,
            colorfmt=self.colorfmt,
            bufferfmt=self.bufferfmt
        )






class KinectView(TextureView):


    def __init__(self, **kwargs):
        self.preprocessors = []

        super().__init__(colorfmt='luminance', **kwargs)
        self.register_event_type('on_frame')
        #self.bind(on_frame=self.update_frame)


    def on_texture_allocated(self, *args):
        w, h = self.texture_size
        self.size = 2*w, 2*h


    def add_preprocessor(self, preprocessor):
        self.preprocessors.append(preprocessor)


    def clear_preprocess(self):
        self.preprocessors = []


    def update_frame(self, frame, skip_preprocessors=False):
        self.frame = frame.copy()
        
        if not skip_preprocessors:
            for proc in self.preprocessors:
                if isinstance(proc, KinectFramePreprocessor):
                    frame = proc.apply(frame)
                elif callable(proc):
                    frame = proc(frame)
                else:
                    raise ValueError('Invalid preprocessor: ', proc.__name__)

        self.processed_frame = processed_frame = frame.copy()

        frame = (frame % 256).astype(np.uint8)
        #frame = (((frame/(2 ** 16)) ** 0.32) * 256).astype(np.uint8)   # gamma correction for ir frame
        
        frame = frame.astype(np.uint8)

        h, w = frame.shape[0:2]
        if self.texture_size != [w, h]:
            self.texture_size = [w, h]

        self.blit_to_texture(frame.tostring())
        self.canvas.ask_update()
        self.dispatch('on_frame', self.frame, self.processed_frame)


    def on_frame(self, frame, processed_frame):
        pass


    def get_depth_coordination(self, cursor_xy, radius=1, processed=False):

        x, y = np.array(cursor_xy) - np.array(self.pos)
        ww, wh = self.size
        #x, y = ww - x, wh - y #flip coords

        kw, kh = self.texture_size
        x, y = int(x * kw/ww), int(y * kh/wh)

        if not processed:
            frame = self.frame.copy()
        else:
            frame = self.processed_frame.copy()

        tw, th = self.texture_size
        frame = frame.reshape(th, tw)     ################### THIS NEED TO BE CHANGED
        r = radius
        local_region = frame[y-r+1:y+r, x-r+1:x+r]
        avg = np.average(local_region.reshape(-1))
        pix = float(avg)

        depth_corner = [x, y, pix]
        return depth_corner








class KinectFramePreprocessor:

    def __init__(self, name=None):
        if name:
            self._name = name
        else:
            self._name = self.__class__.__name__

    def apply(self, frame):
        raise NotImplementedError

    def name(self):
        return self._name




class Clipper(KinectFramePreprocessor):

    def __init__(self, near=800, far=1200, **kw):
        super().__init__(**kw)
        self.near = near
        self.far = far


    def apply(self, frame):
        near, far = self.near, self.far
        diff = far - near
        self.frame = frame.copy()
        frame = frame - near
        frame[frame < 0] = 0
        frame[frame > diff] = 0
        frame = frame * (255.0 / diff)

        return frame




class PlaneSubstractor(KinectFramePreprocessor):


    def __init__(self):
        self.ready = False
        self.frame_size = None
        self.margin = 40



    def set_plane(self, center, dz_per_x_pixel, dz_per_y_pixel):        
        self.center = center
        self.dz_per_x_pixel = dz_per_x_pixel
        self.dz_per_y_pixel = dz_per_y_pixel

        if self.frame_size:
            self._set_plane()

        self.ready = True



    def _set_plane(self):
        dz_per_x_pixel = self.dz_per_x_pixel
        dz_per_y_pixel = self.dz_per_y_pixel

        bw, bh = self.frame_size    ################################ need inprove here!!!
        x, y, z = self.center
        
        #dz = bw * (zpn-znn)/(xpn-xnn)
        dz = -bw * dz_per_x_pixel
        x_linspace = np.linspace(-(x/bw) * dz, (1-x/bw) * dz, num=bw)
        self.buffer_x_correction = np.tile(x_linspace, (bh, 1))

        #dz = bh * (znp-znn)/(ynp-ynn)
        dz = -bh * dz_per_y_pixel
        y_linspace = np.linspace(-(y/bh) * dz, (1-y/bh) * dz , num=bh)
        buffer_y_correction = np.tile(y_linspace, (bw, 1))
        self.buffer_y_correction = buffer_y_correction.transpose()

        self.zoffset = z + self.margin




    def apply(self, frame):
        if not self.ready:
            return frame

        fshape = frame.shape[1], frame.shape[0]
        if self.frame_size != fshape:
            self.frame_size = fshape
            self._set_plane()

        frame = frame - self.buffer_x_correction
        frame = frame - self.buffer_y_correction

        frame = frame - self.zoffset
        #frame[frame < 0] = 0
        
        #gain = 255 / 100
        #frame = frame * gain
        #frame[frame > 255] = 0

        return frame











