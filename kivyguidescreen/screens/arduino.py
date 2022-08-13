from serial.tools import list_ports

from kivy.clock import Clock

from kivyguidescreen import GuideScreen, GuideScreenManager



class SelectArduinoPortScreen(GuideScreen):

    
    def __init__(self, **kw):
        super().__init__(**kw)
        

    def on_enter(self):
        self.monitor_ports_routine = Clock.schedule_interval(self.monitor_ports, 1/60)


    def on_pre_leave(self):
        self.monitor_ports_routine.cancel()
        super().on_pre_leave()


    def monitor_ports(self, dt=0):
        listportinfo = list_ports.comports()
        num_ports = len(listportinfo)

        if num_ports == 0:
            self.guide = "請將校正器的 USB 線插上電腦"
        elif num_ports == 1:
            port, desc, hwid= listportinfo[0]
            self.upload_to_manager(arduino_guage_port=port)
            self.goto_next_screen()
        else:
            str_portsinfo = ''
            self.port_options = {}
            for index, info in enumerate(listportinfo):
                port, desc, hwid= info
                str_portsinfo += "{index}.  {port}:   {desc}\n\n".format(index=index+1, port=port, desc=desc)
                self.port_options[str(index+1)] = port
                
            self.guide = "請輸入數字選擇校正器所在的埠口:\n\n{str_portsinfo}".format(str_portsinfo=str_portsinfo)


    def on_key_down(self, keyname, modifiers):
        port_options = self.port_options
        if keyname.isdigit():
            if keyname in port_options:
                port = port_options[keyname]
                self.upload_to_manager(arduino_guage_port=port)
                self.goto_next_screen()


    def undo(self):
        self.goto_previous_screen()



 
from kivy.lang import Builder
Builder.load_string("""


<SelectArduinoPortScreen>:
    cursor: 'hidden'
    #background: {colors.Y}


""".format(colors=GuideScreenManager.colors))
 