from abc import ABC, abstractmethod
import numpy as np
from scipy.optimize import curve_fit, minimize
import time
import cv2
import os
import logging

class ICellAcquisition(ABC):
    def __init__(self, microscope, directory_setup):
        self.microscope = microscope
        self.directory_setup = directory_setup
        self.acquired_cell_images_dir = self.directory_setup.get_directory("acquired_cell_images")

    @abstractmethod
    def acquire_cell(self, cell_coordinates):
        pass

class CustomCellAcquisition(ICellAcquisition):
    def __init__(self, microscope, directory_setup):
        super().__init__(microscope, directory_setup)
        self.image_width = 680
        self.image_height = 510
        self.image_center = (self.image_width // 2, self.image_height // 2)
        
        # Adjust these values based on your microscope's specifications
        self.pixel_to_um_ratio_x = 0.3  # Estimate: 0.3 micrometers per pixel
        self.pixel_to_um_ratio_y = 0.3  # Adjust if aspect ratio is different

    def acquire_cell(self, cell_coordinates):
        try:
            initial_x, initial_y = self.microscope.stage.x, self.microscope.stage.y
            
            # First move
            dx_pixels, dy_pixels = self.calculate_pixel_distance(cell_coordinates)
            dx_um = dx_pixels * self.pixel_to_um_ratio_x
            dy_um = dy_pixels * self.pixel_to_um_ratio_y

            logging.debug(f"Initial move: dx={dx_um}μm, dy={dy_um}μm")
            self.microscope.stage.move(x=initial_x + dx_um, y=initial_y + dy_um)
            time.sleep(1)

            # Capture image and check centering
            image = self.microscope.capture_image()
            cell_center = self.find_cell_center(image)
            
            # Fine-tune movement
            if cell_center:
                dx_pixels, dy_pixels = self.calculate_pixel_distance(cell_center)
                dx_um = dx_pixels * self.pixel_to_um_ratio_x * 0.5  # Apply 50% correction
                dy_um = dy_pixels * self.pixel_to_um_ratio_y * 0.5
                
                logging.debug(f"Fine-tune move: dx={dx_um}μm, dy={dy_um}μm")
                self.microscope.stage.move(x=self.microscope.stage.x + dx_um, y=self.microscope.stage.y + dy_um)
                time.sleep(1)
                
                image = self.microscope.capture_image()

            # Draw cross and save image
            draw_image = self.draw_cross_on_image(image)
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"acquired_cell_{timestamp}.png"
            filepath = os.path.join(self.acquired_cell_images_dir, filename)
            cv2.imwrite(filepath, draw_image)

            return draw_image, filepath

        except Exception as e:
            logging.exception("Error in acquire_cell method")
            raise

    def calculate_pixel_distance(self, coordinates):
        return self.image_center[0] - coordinates[0], self.image_center[1] - coordinates[1]

    def find_cell_center(self, image):
        # Implement cell detection here. For now, we'll use a simple method.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                return (cx, cy)
        return None

    def draw_cross_on_image(self, image):
        draw_image = image.copy()
        cross_color = (0, 0, 255)  # Red in BGR
        cross_size = 20
        cv2.line(draw_image, (self.image_center[0] - cross_size, self.image_center[1]),
                 (self.image_center[0] + cross_size, self.image_center[1]), cross_color, 2)
        cv2.line(draw_image, (self.image_center[0], self.image_center[1] - cross_size),
                 (self.image_center[0], self.image_center[1] + cross_size), cross_color, 2)
        return draw_image

    def log_image_info(self, step_name, image):
        logging.debug(f"{step_name} - Shape: {image.shape}, dtype: {image.dtype}, min: {np.min(image)}, max: {np.max(image)}")

    def calibrate(self):
        print("Starting calibration...")
        # Move the stage by known distances
        movements = [(10, 0), (0, 10), (20, 0), (0, 20)]
        pixel_displacements = []

        initial_image = self.microscope.capture_image()
        initial_x, initial_y = self.microscope.stage.x, self.microscope.stage.y

        for dx, dy in movements:
            self.microscope.stage.move(x=initial_x + dx, y=initial_y + dy)
            time.sleep(1)  # Wait for stage to settle
            moved_image = self.microscope.capture_image()
            
            # Calculate pixel displacement
            pixel_dx, pixel_dy, _ = self.calculate_displacement(initial_image, moved_image)
            pixel_displacements.append((pixel_dx, pixel_dy))
            
            # Move back to initial position
            self.microscope.stage.move(x=initial_x, y=initial_y)
            time.sleep(1)

        # Calculate average ratio
        ratios = []
        for (dx, dy), (pixel_dx, pixel_dy) in zip(movements, pixel_displacements):
            if dx != 0:
                ratios.append(abs(dx / pixel_dx))
            if dy != 0:
                ratios.append(abs(dy / pixel_dy))

        self.pixel_to_um_ratio = np.mean(ratios)
        print(f"Calibration complete. Pixel to micrometer ratio: {self.pixel_to_um_ratio}")


    def fit_model(self, commanded, measured):
        def model_func(x, a, b, c):
            return a * x**3 + b * x + c

        popt, _ = curve_fit(model_func, commanded, measured)
        return lambda x: model_func(x, *popt)

    def compensate_movement(self, target_dx, target_dy):
        if self.x_model is None or self.y_model is None:
            raise ValueError("Compensator not calibrated. Run calibrate() first.")

        def objective(x):
            return (self.x_model(x[0]) - target_dx)**2 + (self.y_model(x[1]) - target_dy)**2

        result = minimize(objective, [target_dx, target_dy], method='Nelder-Mead')
        return result.x

    # def acquire_cell(self, cell_coordinates):
    #     try:
    #         current_x, current_y = self.microscope.stage.x, self.microscope.stage.y
    #         image_center_x = self.microscope.camera.width // 2
    #         image_center_y = self.microscope.camera.height // 2

    #         dx = (image_center_x - cell_coordinates[0]) * self.pixel_to_um_ratio
    #         dy = (image_center_y - cell_coordinates[1]) * self.pixel_to_um_ratio

    #         logging.debug(f"Moving stage by dx={dx}, dy={dy}")
    #         self.microscope.stage.move(x=current_x + dx, y=current_y + dy)
    #         time.sleep(1)

    #         image = self.microscope.capture_image()
    #         self.log_image_info("Captured image", image)

    #         # Ensure the image is in the correct format for OpenCV operations
    #         if isinstance(image, np.ndarray):
    #             if image.dtype != np.uint8:
    #                 logging.debug("Converting image to uint8")
    #                 image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    #                 self.log_image_info("After normalization", image)
                
    #             if len(image.shape) == 2:
    #                 logging.debug("Converting grayscale to BGR")
    #                 image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    #                 self.log_image_info("After grayscale to BGR conversion", image)
    #             elif image.shape[2] == 4:
    #                 logging.debug("Converting RGBA to BGR")
    #                 image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    #                 self.log_image_info("After RGBA to BGR conversion", image)
    #         else:
    #             raise ValueError(f"Captured image is not a numpy array. Type: {type(image)}")

    #         # Save the processed image before drawing
    #         self.save_debug_image(image, "before_drawing.png")

    #         # Draw a red cross at the center of the image
    #         cross_color = (0, 0, 255)  # Red in BGR
    #         cross_size = 20
    #         try:
    #             cv2.line(image, (image_center_x - cross_size, image_center_y),
    #                      (image_center_x + cross_size, image_center_y), cross_color, 2)
    #             cv2.line(image, (image_center_x, image_center_y - cross_size),
    #                      (image_center_x, image_center_y + cross_size), cross_color, 2)
    #         except cv2.error as e:
    #             logging.error(f"OpenCV error while drawing lines: {str(e)}")
    #             self.log_image_info("Image causing OpenCV error", image)
    #             raise

    #         timestamp = time.strftime("%Y%m%d-%H%M%S")
    #         filename = f"acquired_cell_{timestamp}.png"
    #         filepath = os.path.join(self.acquired_cell_images_dir, filename)
    #         cv2.imwrite(filepath, image)

    #         return image, filepath

    #     except Exception as e:
    #         logging.exception("Error in acquire_cell method")
    #         raise

    # def log_image_info(self, step_name, image):
    #     logging.debug(f"{step_name} - Shape: {image.shape}, dtype: {image.dtype}, min: {np.min(image)}, max: {np.max(image)}")

    def save_debug_image(self, image, filename):
        debug_filepath = os.path.join(self.acquired_cell_images_dir, filename)
        cv2.imwrite(debug_filepath, image)
        logging.debug(f"Debug image saved to {debug_filepath}")

    def display_debug_info(self, image, cell_coordinates, dx, dy):
        try:
            debug_image = image.copy()
            height, width = debug_image.shape[:2]
            cv2.putText(debug_image, f"Cell: {cell_coordinates}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(debug_image, f"Move: ({dx:.2f}, {dy:.2f})", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.circle(debug_image, tuple(map(int, cell_coordinates)), 10, (255, 0, 0), 2)
            debug_filepath = os.path.join(self.acquired_cell_images_dir, "debug_image.png")
            cv2.imwrite(debug_filepath, debug_image)
            logging.debug(f"Debug image saved to {debug_filepath}")
        except Exception as e:
            logging.exception("Error in display_debug_info method")

    def calculate_displacement(self, img1, img2):
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        sift = cv2.SIFT_create()
        
        kp1, des1 = sift.detectAndCompute(gray1, None)
        kp2, des2 = sift.detectAndCompute(gray2, None)
        
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)
        
        good_matches = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good_matches.append(m)
        
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        
        dx = M[0, 2]
        dy = M[1, 2]
        rotation = np.arctan2(M[1, 0], M[0, 0]) * 180 / np.pi
        
        return dx, dy, rotation
    
    def find_cell_in_image(self, image, original_coordinates):
        # Implement a method to find the cell in the new image
        # This could use template matching or feature detection
        # For now, we'll use a simple method that looks for the brightest spot near the expected location
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        search_radius = 50
        x1 = max(0, original_coordinates[0] - search_radius)
        x2 = min(image.shape[1], original_coordinates[0] + search_radius)
        y1 = max(0, original_coordinates[1] - search_radius)
        y2 = min(image.shape[0], original_coordinates[1] + search_radius)
        roi = gray[y1:y2, x1:x2]
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(roi)
        return (x1 + max_loc[0], y1 + max_loc[1])