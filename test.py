# Test Script
from Controller import controller
from Microscope import Microscope
from Autofocus import Amplitude, Phase, RamanSpectra

controller.config_file = "IX81_LUDL_amscope_Laser532.cfg"

ms = Microscope()

ms.camera.set_option("Binning", "1x1")
ms.camera.set_option("PixelType", "GREY8")
ms.camera.set_option("ExposureAuto", "0")
ms.camera.set_exposure(17)

result = ms.auto_focus(strategy=Amplitude, start=1350, end=1400)
print(result)