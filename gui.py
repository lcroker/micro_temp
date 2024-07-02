from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QHBoxLayout
from PyQt5.QtGui import QPixmap, QImage
import sys
from microscope import Microscope
from autofocus import Amplitude, Phase, RamanSpectra
from controller import controller
import numpy as np

class MicroscopeControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microscope Control")
        self.setGeometry(100, 100, 1000, 800)

        # Initialize microscope components
        controller.config_file = "IX81_LUDL_amscope_Laser532.cfg"
        self.microscope = Microscope()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Camera Control Section
        camera_control_layout = QVBoxLayout()
        main_layout.addLayout(camera_control_layout)
        
        camera_control_label = QLabel("Camera Control")
        camera_control_layout.addWidget(camera_control_label)

        self.binning_input = QComboBox()
        self.binning_input.addItems(["1x1", "2x2", "4x4"])
        camera_control_layout.addWidget(QLabel("Binning"))
        camera_control_layout.addWidget(self.binning_input)

        self.pixel_type_input = QComboBox()
        self.pixel_type_input.addItems(["GREY8", "GREY16", "RGB24"])
        camera_control_layout.addWidget(QLabel("Pixel Type"))
        camera_control_layout.addWidget(self.pixel_type_input)

        self.exposure_input = QLineEdit()
        camera_control_layout.addWidget(QLabel("Exposure (ms)"))
        camera_control_layout.addWidget(self.exposure_input)

        self.set_camera_button = QPushButton("Set Camera Options")
        camera_control_layout.addWidget(self.set_camera_button)

        # Autofocus Control Section
        autofocus_control_layout = QVBoxLayout()
        main_layout.addLayout(autofocus_control_layout)

        autofocus_control_label = QLabel("Autofocus Control")
        autofocus_control_layout.addWidget(autofocus_control_label)

        self.start_position_input = QLineEdit()
        autofocus_control_layout.addWidget(QLabel("Start Position"))
        autofocus_control_layout.addWidget(self.start_position_input)

        self.end_position_input = QLineEdit()
        autofocus_control_layout.addWidget(QLabel("End Position"))
        autofocus_control_layout.addWidget(self.end_position_input)

        self.step_size_input = QLineEdit()
        autofocus_control_layout.addWidget(QLabel("Step Size"))
        autofocus_control_layout.addWidget(self.step_size_input)

        self.autofocus_button = QPushButton("Start Autofocus")
        autofocus_control_layout.addWidget(self.autofocus_button)

        # Stage Control Section
        stage_control_layout = QVBoxLayout()
        main_layout.addLayout(stage_control_layout)

        stage_control_label = QLabel("Stage Control")
        stage_control_layout.addWidget(stage_control_label)

        self.stage_x_input = QLineEdit()
        stage_control_layout.addWidget(QLabel("X Position"))
        stage_control_layout.addWidget(self.stage_x_input)

        self.stage_y_input = QLineEdit()
        stage_control_layout.addWidget(QLabel("Y Position"))
        stage_control_layout.addWidget(self.stage_y_input)

        self.stage_z_input = QLineEdit()
        stage_control_layout.addWidget(QLabel("Z Position"))
        stage_control_layout.addWidget(self.stage_z_input)

        self.move_stage_button = QPushButton("Move Stage")
        stage_control_layout.addWidget(self.move_stage_button)

        # Image Capture Section
        image_capture_layout = QVBoxLayout()
        main_layout.addLayout(image_capture_layout)

        image_capture_label = QLabel("Image Capture")
        image_capture_layout.addWidget(image_capture_label)

        self.capture_image_button = QPushButton("Capture Image")
        image_capture_layout.addWidget(self.capture_image_button)

        # Display Captured Image
        self.image_label = QLabel()
        image_capture_layout.addWidget(self.image_label)

        # Test Script Button
        self.test_script_button = QPushButton("Run Test Script")
        main_layout.addWidget(self.test_script_button)

        # Output Area
        self.output_area = QTextEdit()
        main_layout.addWidget(QLabel("Output"))
        main_layout.addWidget(self.output_area)

        # Connect signals to slots
        self.set_camera_button.clicked.connect(self.set_camera_options)
        self.autofocus_button.clicked.connect(self.start_autofocus)
        self.move_stage_button.clicked.connect(self.move_stage)
        self.capture_image_button.clicked.connect(self.capture_image)
        self.test_script_button.clicked.connect(self.run_test_script)

    def set_camera_options(self):
        binning = self.binning_input.currentText()
        pixel_type = self.pixel_type_input.currentText()
        exposure = self.exposure_input.text()
        self.output_area.append(f"Setting camera options: Binning={binning}, Pixel Type={pixel_type}, Exposure={exposure}ms")
        self.microscope.camera.set_option("Binning", binning)
        self.microscope.camera.set_option("PixelType", pixel_type)
        self.microscope.camera.set_exposure(int(exposure))

    def start_autofocus(self):
        start = int(self.start_position_input.text())
        end = int(self.end_position_input.text())
        step = float(self.step_size_input.text())
        self.output_area.append(f"Starting autofocus: Start={start}, End={end}, Step={step}")
        result = self.microscope.auto_focus(strategy=Amplitude, start=start, end=end, step=step)
        self.output_area.append(f"Autofocus result: Optimal position={result}")

    def move_stage(self):
        x_text = self.stage_x_input.text()
        y_text = self.stage_y_input.text()
        z_text = self.stage_z_input.text()

        try:
            x = float(x_text) if x_text else None
        except ValueError:
            self.output_area.append(f"Invalid X position: {x_text}")
            return

        try:
            y = float(y_text) if y_text else None
        except ValueError:
            self.output_area.append(f"Invalid Y position: {y_text}")
            return

        try:
            z = float(z_text) if z_text else None
        except ValueError:
            self.output_area.append(f"Invalid Z position: {z_text}")
            return

        self.output_area.append(f"Moving stage to: X={x}, Y={y}, Z={z}")
        self.microscope.stage.move(x=x, y=y, z=z)
        self.output_area.append(f"Finished Moving!")

    def capture_image(self):
        self.output_area.append("Capturing image...")
        try:
            self.microscope.lamp.set_on()
            image = self.microscope.camera.capture()
            if image is not None:
                self.image_label.clear()  # Clear the previous image
                self.display_image(image)
                self.output_area.append("Image captured successfully.")
            else:
                self.output_area.append("Failed to capture image.")
            self.microscope.lamp.set_off()
        except Exception as e:
            self.output_area.append(f"Error capturing image: {e}")

    def display_image(self, image):
        if image is not None:
            height, width = image.shape
            bytes_per_line = width
            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image)
            self.image_label.setPixmap(pixmap.scaled(400, 300))

    def run_test_script(self):
        self.output_area.append("Running test script...")
        self.microscope.camera.set_option("Binning", "1x1")
        self.microscope.camera.set_option("PixelType", "GREY8")
        self.microscope.camera.set_option("ExposureAuto", "0")
        self.microscope.camera.set_exposure(17)
        result = self.microscope.auto_focus(strategy=Amplitude, start=1350, end=1400)
        self.output_area.append(f"Test script result: {result}")

def main():
    app = QApplication(sys.argv)
    window = MicroscopeControlApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
