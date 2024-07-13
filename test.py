import os
import numpy as np
import cv2
from microscope import Microscope
from directory_setup import DirectorySetup
import matplotlib.pyplot as plt
import time

def create_test_folder():
    test_folder = "test"
    if not os.path.exists(test_folder):
        os.makedirs(test_folder)
    return test_folder

def capture_image(microscope):
    microscope.lamp.set_on()
    time.sleep(4)
    for _ in range(4):
        image = microscope.camera.snap_image()
        time.sleep(0.6)
    image = microscope.camera.snap_image()
    microscope.lamp.set_off()
    return image

def calculate_displacement(img1, img2):
    # Convert images to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    # Initialize SIFT detector
    sift = cv2.SIFT_create()
    
    # Find keypoints and descriptors
    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)
    
    # FLANN parameters
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks = 50)
    
    # FLANN-based matcher
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)
    
    # Apply ratio test
    good_matches = []
    for m, n in matches:
        if m.distance < 0.7 * n.distance:
            good_matches.append(m)
    
    # Extract matched keypoints
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    
    # Find homography
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    
    # Calculate displacement and rotation
    dx = M[0, 2]
    dy = M[1, 2]
    rotation = np.arctan2(M[1, 0], M[0, 0]) * 180 / np.pi
    
    return dx, dy, rotation

def test_stage_movement(microscope, test_folder):
    # Define movements to test (in micrometers)
    movements = [(10, 0), (0, 10), (10, 10), (-10, 0), (0, -10), (-10, -10)]
    
    results = []
    
    # Capture initial image
    initial_image = capture_image(microscope)
    cv2.imwrite(os.path.join(test_folder, "initial_image.png"), initial_image)
    
    for dx, dy in movements:
        # Move stage
        current_x, current_y = microscope.stage.x, microscope.stage.y
        microscope.stage.move(x=current_x + dx, y=current_y + dy)
        
        # Wait for stage movement to settle
        time.sleep(2)
        
        # Capture image after movement
        moved_image = capture_image(microscope)
        cv2.imwrite(os.path.join(test_folder, f"moved_image_{dx}_{dy}.png"), moved_image)
        
        # Calculate displacement and rotation
        measured_dx, measured_dy, rotation = calculate_displacement(initial_image, moved_image)
        
        # Convert pixel displacement to micrometers (assuming 1 pixel = 0.1 micrometer, adjust as needed)
        pixel_to_um = 0.1
        measured_dx_um = measured_dx * pixel_to_um
        measured_dy_um = measured_dy * pixel_to_um
        
        results.append({
            "commanded_movement": (dx, dy),
            "measured_movement": (measured_dx_um, measured_dy_um),
            "rotation": rotation
        })
        
        # Reset stage position
        microscope.stage.move(x=current_x, y=current_y)
        time.sleep(2)  # Wait for stage to return to initial position
    
    return results

def plot_results(results, test_folder):
    commanded_x = [r["commanded_movement"][0] for r in results]
    commanded_y = [r["commanded_movement"][1] for r in results]
    measured_x = [r["measured_movement"][0] for r in results]
    measured_y = [r["measured_movement"][1] for r in results]
    rotations = [r["rotation"] for r in results]
    
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    
    ax1.scatter(commanded_x, measured_x)
    ax1.plot([min(commanded_x), max(commanded_x)], [min(commanded_x), max(commanded_x)], 'r--')
    ax1.set_xlabel("Commanded X Movement (µm)")
    ax1.set_ylabel("Measured X Movement (µm)")
    ax1.set_title("X Axis Movement")
    
    ax2.scatter(commanded_y, measured_y)
    ax2.plot([min(commanded_y), max(commanded_y)], [min(commanded_y), max(commanded_y)], 'r--')
    ax2.set_xlabel("Commanded Y Movement (µm)")
    ax2.set_ylabel("Measured Y Movement (µm)")
    ax2.set_title("Y Axis Movement")
    
    ax3.bar(range(len(rotations)), rotations)
    ax3.set_xlabel("Measurement Number")
    ax3.set_ylabel("Rotation (degrees)")
    ax3.set_title("Camera Rotation")
    
    plt.tight_layout()
    plt.savefig(os.path.join(test_folder, "movement_results.png"))
    plt.close()

def main():
    test_folder = create_test_folder()
    
    # Initialize microscope
    config_file = "C:\\Users\\Raman1\\Desktop\\luke_github\\super_temp\\IX81_LUDL_amscope_Laser532.cfg"  # Update this path
    directory_setup = DirectorySetup()
    microscope = Microscope(config_file, directory_setup)
    
    # Run the test
    results = test_stage_movement(microscope, test_folder)
    
    # Plot and save results
    plot_results(results, test_folder)
    
    # Print results
    print("Test Results:")
    for i, r in enumerate(results, 1):
        print(f"Test {i}:")
        print(f"  Commanded: {r['commanded_movement']}")
        print(f"  Measured: {r['measured_movement']}")
        print(f"  Rotation: {r['rotation']:.2f} degrees")
    
    # Shutdown microscope
    microscope.shutdown()

if __name__ == "__main__":
    main()