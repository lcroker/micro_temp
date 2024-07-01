from Controller import controller

class Lamp:

    def __init__(self):
        self.controller = controller

    def set_on(self):
        self.controller.set_property("TransmittedLamp", "Label", "On")
    
    def set_off(self):
        self.controller.set_property("TransmittedLamp", "Label", "Off")