from Camera import ICamera, Camera, SpectralCamera
from Stage import Stage
from Lamp import Lamp
from Autofocus import Autofocus

class Microscope:

    def __init__(self):
        self.camera:ICamera = Camera()
        self.stage:Stage = Stage()
        self.lamp:Lamp = Lamp()
        
    def auto_focus(self, strategy:Autofocus, start, end, step=1):
        self.focus_strategy = strategy(self.camera, self.stage, self.lamp)
        return self.focus_strategy.focus(start, end, step)


