from Controller import controller

class Stage:
    def __init__(self):
        self.controller = controller
        self.focus_device = self.controller.get_focus_device()
        self.xy_stage_device = self.controller.get_xy_stage_device()
        self.x = self.controller.get_x_position(self.xy_stage_device)
        self.y = self.controller.get_y_position(self.xy_stage_device)
        self.z = self.controller.get_position(self.focus_device)
    
    def move(self, x=None, y=None, z=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if z is not None:
            self.z = z
        
        self.controller.set_xy_position(self.xy_stage_device, self.x, self.y)
        self.controller.set_position(self.focus_device, self.z)