
import cv2
import numpy as np

class Ball:
    def __init__(self, color, pixel_position, frame_shape, perspective_matrix, field_height_cm=500):
        self.color = color  # "Red", "Blue", "Jack"
        self.pixel_position = np.float32([pixel_position])  # (x, y) in pixels
        self.frame_shape = frame_shape  # (height, width)
        self.matrix = perspective_matrix
        self.field_height_cm = field_height_cm

        # Convert to real-world position
        self.x_cm, self.y_cm = self.convert_to_real_world()

        # Compute distance from bottom edge
        self.bottom_distance_cm = self.calculate_distance_from_bottom()

    def convert_to_real_world(self):
        point = self.pixel_position.reshape(1, 1, 2)
        transformed = cv2.perspectiveTransform(point, self.matrix)
        x_cm, y_cm = transformed[0][0]
        return x_cm, y_cm

    def calculate_distance_from_bottom(self):
        return self.field_height_cm - self.y_cm

    def __str__(self):
        return (f"{self.color} ball: Real Position = ({self.x_cm:.2f} cm, {self.y_cm:.2f} cm), "
                f"Distance to Bottom = {self.bottom_distance_cm:.2f} cm")
