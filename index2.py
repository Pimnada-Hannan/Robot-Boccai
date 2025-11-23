from collections import deque
import numpy as np
import argparse
import cv2
import imutils

# Argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True, help="Path to the image file")
ap.add_argument("-b", "--buffer", type=int, default=64, help="Max buffer size")
args = vars(ap.parse_args())

# HSV boundaries for each color
color_bounds = {
    "red": [
        ((0, 100, 100), (10, 255, 255)), 
        ((160, 100, 100), (179, 255, 255))
    ],
    "darkblue": [
        ((100, 150, 0), (110, 255, 255)), 
        ((111, 120, 0), (130, 255, 255))  # Slightly extended into more hues
    ],
    "white": [
        ((0, 0, 200), (180, 30, 255)), 
        ((0, 0, 180), (180, 50, 255))  # Covers slightly dimmer white shades
    ]
}


# Drawing colors (BGR)
draw_colors = {
    "red": (0, 0, 255),
    "darkblue": (255, 0, 0),
    "white": (0, 0, 0)  # black outline for visibility
}

# Load image
frame = cv2.imread(args["image"])
if frame is None:
    print("[ERROR] Image not found or path is incorrect.")
    exit()

# Resize and preprocess
frame = imutils.resize(frame, width=600)
blurred = cv2.GaussianBlur(frame, (11, 11), 0)
hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

# Process each color
for color_name, bounds in color_bounds.items():
    mask = None
    for lower, upper in bounds:
        temp_mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        mask = temp_mask if mask is None else cv2.bitwise_or(mask, temp_mask)

    # Clean mask
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    # Find contours
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    center = None
    if len(cnts) > 0:
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        M = cv2.moments(c)
        if M["m00"] > 0:
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
        else:
            continue

        if radius > 10:
            # For white: use black outline + white dot
            if color_name == "white":
                cv2.circle(frame, (int(x), int(y)), int(radius), (0, 0, 0), 2)  # Black outline
                cv2.circle(frame, center, 5, (255, 255, 255), -1)  # White center
            else:
                cv2.circle(frame, (int(x), int(y)), int(radius), draw_colors[color_name], 2)
                cv2.circle(frame, center, 5, draw_colors[color_name], -1)

            # Put label
            cv2.putText(frame, color_name.upper(), (int(x) - 20, int(y) - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, draw_colors[color_name], 2)

            print(f"{color_name.capitalize()} ball found at ({int(x)}, {int(y)}) | Radius: {int(radius)}")
        else:
            print(f"{color_name.capitalize()} ball detected, but too small.")
    else:
        print(f"No {color_name} ball detected.")

# Show results
cv2.imshow("Detected Balls", frame)
cv2.waitKey(0)
cv2.destroyAllWindows()
