import sys
import os
import logging
import time
import gc
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QFileDialog, QMessageBox, QGroupBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from microscope import Microscope
from autofocus import Amplitude

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MicroManagerInitThread(QThread):
    finished = pyqtSignal(object, str)

    def __init__(self, config_file, app_path):
        super().__init__()
        self.config_file = config_file
        self.app_path = app_path

    def run(self):
        try:
            microscope = Microscope(self.config_file, self.app_path)
            self.finished.emit(microscope, "Micro-Manager started successfully.")
        except Exception as e:
            logging.error(f"Error in MicroManagerInitThread: {e}", exc_info=True)
            self.finished.emit(None, f"Error starting Micro-Manager: {str(e)}")

class MicroscopeControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microscope Control")
        self.setGeometry(100, 100, 1000, 800)
        
        self.mm_app_path = "C:\\Program Files\\Micro-Manager-2.0"
        self.microscope = None
        self.init_thread = None

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Configuration File Selection Section
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        config_group.setLayout(config_layout)

        self.config_file_button = QPushButton("Browse")
        self.config_file_path = QLineEdit()
        self.start_headless_button = QPushButton("Start Micro-Manager")

        config_layout.addWidget(self.config_file_button)
        config_layout.addWidget(self.config_file_path)
        config_layout.addWidget(self.start_headless_button)

        # Camera Control Section
        camera_group = QGroupBox("Camera Control")
        camera_layout = QVBoxLayout()
        camera_group.setLayout(camera_layout)

        self.binning_input = QComboBox()
        self.binning_input.addItems(["1x1", "2x2", "4x4"])
        self.pixel_type_input = QComboBox()
        self.pixel_type_input.addItems(["GREY8", "GREY16", "RGB24"])
        self.exposure_input = QLineEdit()
        self.set_camera_button = QPushButton("Set Camera Options")

        camera_layout.addWidget(QLabel("Binning"))
        camera_layout.addWidget(self.binning_input)
        camera_layout.addWidget(QLabel("Pixel Type"))
        camera_layout.addWidget(self.pixel_type_input)
        camera_layout.addWidget(QLabel("Exposure (ms)"))
        camera_layout.addWidget(self.exposure_input)
        camera_layout.addWidget(self.set_camera_button)

        # Autofocus Control Section
        autofocus_group = QGroupBox("Autofocus Control")
        autofocus_layout = QVBoxLayout()
        autofocus_group.setLayout(autofocus_layout)

        self.start_position_input = QLineEdit()
        self.end_position_input = QLineEdit()
        self.step_size_input = QLineEdit()
        self.autofocus_button = QPushButton("Start Autofocus")

        autofocus_layout.addWidget(QLabel("Start Position"))
        autofocus_layout.addWidget(self.start_position_input)
        autofocus_layout.addWidget(QLabel("End Position"))
        autofocus_layout.addWidget(self.end_position_input)
        autofocus_layout.addWidget(QLabel("Step Size"))
        autofocus_layout.addWidget(self.step_size_input)
        autofocus_layout.addWidget(self.autofocus_button)

        # Stage Control Section
        stage_group = QGroupBox("Stage Control")
        stage_layout = QVBoxLayout()
        stage_group.setLayout(stage_layout)

        self.stage_x_input = QLineEdit()
        self.stage_y_input = QLineEdit()
        self.stage_z_input = QLineEdit()
        self.move_stage_button = QPushButton("Move Stage")

        stage_layout.addWidget(QLabel("X Position"))
        stage_layout.addWidget(self.stage_x_input)
        stage_layout.addWidget(QLabel("Y Position"))
        stage_layout.addWidget(self.stage_y_input)
        stage_layout.addWidget(QLabel("Z Position"))
        stage_layout.addWidget(self.stage_z_input)
        stage_layout.addWidget(self.move_stage_button)

        # Image Capture Section
        capture_group = QGroupBox("Image Capture")
        capture_layout = QVBoxLayout()
        capture_group.setLayout(capture_layout)

        self.capture_image_button = QPushButton("Capture Image")
        self.image_label = QLabel()
        self.image_label.setFixedSize(400, 300)
        self.image_label.setStyleSheet("border: 1px solid black;")

        capture_layout.addWidget(self.capture_image_button)
        capture_layout.addWidget(self.image_label)

        # Test Script Button
        self.test_script_button = QPushButton("Run Test Script")

        # Output Area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)

        # Add all sections to main layout
        main_layout.addWidget(config_group)
        main_layout.addWidget(camera_group)
        main_layout.addWidget(autofocus_group)
        main_layout.addWidget(stage_group)
        main_layout.addWidget(capture_group)
        main_layout.addWidget(self.test_script_button)
        main_layout.addWidget(QLabel("Output"))
        main_layout.addWidget(self.output_area)

        # Connect signals to slots
        self.config_file_button.clicked.connect(self.browse_config_file)
        self.start_headless_button.clicked.connect(self.start_micromanager)
        self.set_camera_button.clicked.connect(self.set_camera_options)
        self.autofocus_button.clicked.connect(self.start_autofocus)
        self.move_stage_button.clicked.connect(self.move_stage)
        self.capture_image_button.clicked.connect(self.capture_image)
        self.test_script_button.clicked.connect(self.run_test_script)

    def browse_config_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Configuration File", "", "Config Files (*.cfg);;All Files (*)", options=options)
        if file_name:
            self.config_file_path.setText(file_name)

    def start_micromanager(self):
        config_file = self.config_file_path.text()
        if not config_file:
            QMessageBox.warning(self, "Warning", "Please select a configuration file.")
            return

        self.output_area.append("Starting Micro-Manager...")
        self.start_headless_button.setEnabled(False)

        self.init_thread = MicroManagerInitThread(config_file, self.mm_app_path)
        self.init_thread.finished.connect(self.on_micromanager_init_finished)
        self.init_thread.start()

    def on_micromanager_init_finished(self, microscope, message):
        self.start_headless_button.setEnabled(True)
        self.output_area.append(message)

        if microscope is not None:
            self.microscope = microscope
            QMessageBox.information(self, "Success", "Micro-Manager initialized successfully.")
        else:
            QMessageBox.critical(self, "Error", message)

    def set_camera_options(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        binning = self.binning_input.currentText()
        pixel_type = self.pixel_type_input.currentText()
        exposure = self.exposure_input.text()
        self.output_area.append(f"Setting camera options: Binning={binning}, Pixel Type={pixel_type}, Exposure={exposure}ms")
        self.microscope.camera.set_option("Binning", binning)
        self.microscope.camera.set_option("PixelType", pixel_type)
        self.microscope.camera.set_exposure(int(exposure))

    def start_autofocus(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        start = int(self.start_position_input.text())
        end = int(self.end_position_input.text())
        step = float(self.step_size_input.text())
        self.output_area.append(f"Starting autofocus: Start={start}, End={end}, Step={step}")
        result = self.microscope.auto_focus(strategy=Amplitude, start=start, end=end, step=step)
        self.output_area.append(f"Autofocus result: Optimal position={result}")

    def move_stage(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        x = float(self.stage_x_input.text()) if self.stage_x_input.text() else None
        y = float(self.stage_y_input.text()) if self.stage_y_input.text() else None
        z = float(self.stage_z_input.text()) if self.stage_z_input.text() else None

        self.output_area.append(f"Moving stage to: X={x}, Y={y}, Z={z}")
        self.microscope.stage.move(x=x, y=y, z=z)
        self.output_area.append("Finished Moving!")

    def capture_image(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        self.output_area.append("Capturing image...")
        try:
            self.microscope.lamp.set_on()
            time.sleep(0.5)  # Pause for 2 seconds to allow the lamp to stabilize

            # Additional delay for camera stabilization
            time.sleep(1)  # Adjust as needed based on your camera's requirements

            # Capture multiple frames and discard the first few
            for _ in range(3):
                image = self.microscope.camera.capture()
                time.sleep(0.1)  # Short delay between captures

            if image is not None:
                # Debug statement to check the captured image
                print(f"Image captured with shape: {image.shape}, dtype: {image.dtype}")
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
            # Debug statement to check the QImage parameters
            print(f"Creating QImage with width: {width}, height: {height}, bytes_per_line: {bytes_per_line}")
            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image)
            self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), aspectRatioMode=Qt.KeepAspectRatio))
            self.image_label.setScaledContents(True)


    def run_test_script(self):
        if not self.microscope:
            QMessageBox.warning(self, "Warning", "Please start Micro-Manager first.")
            return
        self.output_area.append("Running test script...")
        self.microscope.camera.set_option("Binning", "1x1")
        self.microscope.camera.set_option("PixelType", "GREY8")
        self.microscope.camera.set_option("ExposureAuto", "0")
        self.microscope.camera.set_exposure(17)
        result = self.microscope.auto_focus(strategy=Amplitude, start=1350, end=1400)
        self.output_area.append(f"Test script result: {result}")

    def closeEvent(self, event):
        if self.microscope:
            self.output_area.append("Shutting down Micro-Manager...")
            QApplication.processEvents()  # Process any pending events
            self.microscope.shutdown()
            self.microscope = None  # Ensure the microscope instance is released
            time.sleep(1)  # Give a short delay for cleanup
            gc.collect()  # Force garbage collection again
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MicroscopeControlApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()