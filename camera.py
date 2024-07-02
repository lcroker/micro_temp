import numpy as np
from abc import ABC, abstractmethod
from Controller import controller

class ICamera(ABC):
    def __init__(self, camera:str):
        self.controller = controller
        self.camera = camera
        self.snapped_image = None
        self.controller.set_camera_device(self.camera)

    def set_option(self, option:str = None, value:str = None):
        self.controller.set_property(self.camera, option, value)

    def set_exposure(self, val:int = 15):
        self.controller.set_exposure(val)

    @abstractmethod
    def capture(self) -> np.array:
        pass


class Camera(ICamera):
    def __init__(self, camera:str='AmScope', exposure:int=15):
        super().__init__(camera)
        self.width = self.controller.get_image_width()
        self.height = self.controller.get_image_height()
        self.set_exposure(exposure)

    def capture(self) -> np.array:
        self.controller.snap_image()
        img = self.controller.get_image()

        byte_depth = self.controller.get_bytes_per_pixel()

        if byte_depth == 1:
            img = np.reshape(img, (self.height, self.width)).astype(np.uint8)
        elif byte_depth == 2:
            img = np.reshape(img, (self.height, self.width)).astype(np.uint16)
        else:
            raise ValueError(f'Invalid byte depth: {byte_depth}')
        
        self.snapped_image = img

        return self.snapped_image


class SpectralCamera(ICamera):
    def __init__(self, camera:str='Andor'):
        super().__init__(camera)
    
    def capture(self) -> np.array:
        # Placeholder implementation
        return np.array([])