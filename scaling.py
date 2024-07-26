import cv2
import numpy as np
import matplotlib.pyplot as plt
 
im1 = "C:\\Users\\BryanH\\Downloads\\img1.tif"
im2 = "C:\\Users\\BryanH\\Downloads\\img2.tif"
 
# Load your images
image1 = cv2.imread(im1, cv2.IMREAD_GRAYSCALE)  # Reference image
image2 = cv2.imread(im2, cv2.IMREAD_GRAYSCALE)  # Translated image
 
# Normalize images to [0, 255] range
image1 = cv2.normalize(image1, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
image2 = cv2.normalize(image2, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
 
# Extract the left half of image1 and the right half of image2
half_width = image1.shape[1] // 2
left_half_image1 = image1[:, :half_width]
right_half_image2 = image2[:, half_width:]
 
# Calculate shift using phase correlation
shift_result = cv2.phaseCorrelate(np.float32(left_half_image1), np.float32(right_half_image2))
detected_shift = shift_result[0]
 
# Account for the initial preprocessing displacement
# Assuming right half of image2 starts half an image width offset from the start of image1
actual_shift_x = detected_shift[0] + half_width
actual_shift_y = detected_shift[1]
 
# Print out the exact shift in pixels
print(f"Exact shift in pixels: X: {actual_shift_x}, Y: {actual_shift_y}")
 
 
#############################################################################################################################
## TEST the following code can be blanked out - it just helps us visualise if we have the correct shifts calculed
# Optional: Visual confirmation
# Create a blank RGB image for visualization
blended_image = np.zeros((left_half_image1.shape[0], left_half_image1.shape[1], 3), dtype=np.uint8)
blended_image[..., 0] = left_half_image1  # Red channel
blended_image[..., 1] = cv2.warpAffine(right_half_image2, np.float32([[1, 0, -detected_shift[0]], [0, 1, -detected_shift[1]]]), (right_half_image2.shape[1], right_half_image2.shape[0]))  # Green channel
 
# Display the images
plt.figure(figsize=(10, 5))
plt.imshow(blended_image)
plt.title('Red/Green Overlay of Shifted and Original Image Halves')
plt.axis('off')
plt.show()
##################################################################################################################################
 
##THE RES OF THE CODE WILL FIND THE MATRIX TRANSFORM THAT RELATES THE CAMER XY PLANE AND THE STAGE XY PLANE
## YOU MUST ENTER THE STAGE X AND Y VALUES THAT RESULTRED IN THE MOVEMENT BETWEEN THE TWO IMAGES
stage_shift_x = 200 #I HAVE JUST GUESSED HERE
stage_shift_Y = 200
 
# Constants: Already known from prior calculations
a = actual_shift_x / stage_shift_x
c = actual_shift_y / stage_shift_x
 
# Calculate theta and M (I.E. ROTATION BETWEEN PLANES AND SCALING FACTOR TO RELATE PIXELS TO MIROMETERS)
theta = np.arctan2(c, a)
M = a / np.cos(theta)  # Use cos since a is associated with cos(theta)
 
# Calculate b and d using theta and M
b = -M * np.sin(theta)
d = M * np.cos(theta)
 
# Print results
print(f"Rotation (theta): {np.degrees(theta)} degrees")
print(f"Scaling (M): {M}")
print(f"Transformation matrix: [[{a:.2f}, {b:.2f}], [{c:.2f}, {d:.2f}]]")
 
###############################################################################################################
#FINALLY WE CAN NOW USE THE INVERSE OF THAT MATRIX TO CALUCLATED THE STAGE MOVEMENT TO RELATE TO ANY DESIRED PIXEL MOVEMENT
 
# Function to predict stage movements (if needed)
def predict_stage_movement(px, py):
    T_inv = np.linalg.inv(np.array([[a, b], [c, d]]))
    return T_inv.dot(np.array([px, py]))
 
# Example use of prediction function
px_shift, py_shift = 100, 50  # Example pixel shifts
stage_movement = predict_stage_movement(px_shift, py_shift)
print(f"Stage X movement: {stage_movement[0]:.2f} um, Stage Y movement: {stage_movement[1]:.2f} um")