import cv2
import numpy as np
import math
from tkinter import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading

# from inference_sdk import InferenceHTTPClient
from ultralytics import YOLO
import pymcprotocol


class FieldMeasureApp:
    # Add this inside your class
    BALL_COLORS = {
        0: ("Blue", (255, 0, 0)),  # Blue
        1: ("White", (255, 255, 255)),  # White
        2: ("Red", (0, 0, 255)),  # Red
    }


6


class FieldMeasureApp:
    # ---------- settings ----------
    PREVIEW_SCALE = 0.5  # main preview size
    LOUPE_SCALE = 2.0  # magnification inside loupe
    LOUPE_WIN = 200  # loupe window side (px)
    FIELD_W_CM = 400.0  # set real width here
    FIELD_H_CM = 500.0  # set real height here
    LOUPE_BORDER = 2  # Border thickness for loupe
    LOUPE_BORDER_COLOR = (0, 255, 0)  # Green border
    TARGET_COLOR = (0, 0, 255)  # Red color for the target dot
    TARGET_RADIUS = 2
    WHITE_COLOR_LOWER = np.array([190, 200, 200], np.uint8)
    WHITE_COLOR_UPPER = np.array([255, 255, 255], np.uint8)
    MIN_BALL_RADIUS = 12  # Minimum radius (in pixels) to consider a ball
    BALL_CIRCULARITY_THRESHOLD = 0.65  # Minimum circularity to consider a ball
    # --------------------------------

    def __init__(self, root):
        self.root = root
        self.root.title("Field Measurement Tool")

        # Initialize variables
        self.img = None
        self.preview = None
        self.cap = None
        self.camera_mode = False
        self.field_pts = []
        self.ball_pt1 = None
        self.ball_all = []
        self.cursor_preview = (0, 0)
        self.ball_detected = False
        self.running = True

        # Create UI
        self.yolo_model = YOLO(
            "best.pt"
        )  # Make sure the model file is in the correct path
        self.detection_threshold = 0.01

        # Create UI
        self.create_widgets()

        # Start camera thread if in camera mode
        self.camera_thread = None
        # Call detect_ball every 5 seconds
        # self.detect_ball_timer()

    # def detect_ball_timer(self):
    #     if self.running:
    #         self.detect_ball()
    #         self.root.after(5000, self.detect_ball_timer)

    def create_widgets(self):
        # Frame for image display
        self.image_frame = Frame(self.root)
        self.image_frame.pack(side=LEFT, padx=10, pady=10)

        # Main image canvas
        self.canvas = Canvas(self.image_frame, width=800, height=600)
        self.canvas.pack()
        self.canvas.bind("<Motion>", self.update_loupe)
        self.canvas.bind("<Button-1>", self.add_point)

        # Loupe display
        self.loupe_label = Label(self.image_frame)
        self.loupe_label.pack()

        # Threshold display
        self.thresh_label = Label(self.image_frame)
        self.thresh_label.pack()

        # Control panel
        self.control_frame = Frame(self.root)
        self.control_frame.pack(side=RIGHT, padx=10, pady=10)

        # File operations
        Label(self.control_frame, text="Input Mode", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=5
        )
        Button(
            self.control_frame, text="Open Image File", command=self.open_image_file
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        Button(self.control_frame, text="Open Camera", command=self.open_camera).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=2
        )
        self.capture_btn = Button(
            self.control_frame,
            text="Capture Frame",
            command=self.capture_frame,
            state=DISABLED,
        )
        self.capture_btn.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)

        # Field corners
        Label(
            self.control_frame, text="Field Corners", font=("Arial", 12, "bold")
        ).grid(row=4, column=0, columnspan=2, pady=5)
        self.corner_listbox = Listbox(self.control_frame, height=4, width=30)
        self.corner_listbox.grid(row=5, column=0, columnspan=2, pady=2)
        Button(
            self.control_frame, text="Remove Last", command=self.remove_last_point
        ).grid(row=6, column=0, sticky="ew", pady=2)
        Button(self.control_frame, text="Clear All", command=self.clear_points).grid(
            row=6, column=1, sticky="ew", pady=2
        )

        # Ball detection
        Label(
            self.control_frame, text="Ball Detection", font=("Arial", 12, "bold")
        ).grid(row=7, column=0, columnspan=2, pady=5)
        Button(self.control_frame, text="Detect Ball", command=self.detect_ball).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=2
        )
        self.ball_status = Label(self.control_frame, text="Ball: Not detected")
        self.ball_status.grid(row=9, column=0, columnspan=2, pady=2)

        # Color threshold controls
        Label(
            self.control_frame, text="White Threshold", font=("Arial", 12, "bold")
        ).grid(row=10, column=0, columnspan=2, pady=5)

        # Lower threshold controls
        # Lower threshold controls (HSV)
        Label(self.control_frame, text="Lower HSV:").grid(
            row=11, column=0, columnspan=2, sticky="w"
        )
        self.lower_h = Scale(
            self.control_frame,
            from_=0,
            to=179,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.lower_h.set(self.WHITE_COLOR_LOWER[0])
        self.lower_h.grid(row=12, column=0, sticky="ew")
        self.lower_s = Scale(
            self.control_frame,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.lower_s.set(self.WHITE_COLOR_LOWER[1])
        self.lower_s.grid(row=13, column=0, sticky="ew")
        self.lower_v = Scale(
            self.control_frame,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.lower_v.set(self.WHITE_COLOR_LOWER[2])
        self.lower_v.grid(row=14, column=0, sticky="ew")

        # Upper threshold controls (HSV)
        self.upper_h = Scale(
            self.control_frame,
            from_=0,
            to=179,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.upper_h.set(self.WHITE_COLOR_UPPER[0])
        self.upper_h.grid(row=12, column=1, sticky="ew")
        self.upper_s = Scale(
            self.control_frame,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.upper_s.set(self.WHITE_COLOR_UPPER[1])
        self.upper_s.grid(row=13, column=1, sticky="ew")
        self.upper_v = Scale(
            self.control_frame,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.upper_v.set(self.WHITE_COLOR_UPPER[2])
        self.upper_v.grid(row=14, column=1, sticky="ew")

        # Ball detection parameters
        Label(
            self.control_frame, text="Detection Params", font=("Arial", 12, "bold")
        ).grid(row=15, column=0, columnspan=2, pady=5)
        Label(self.control_frame, text="Min Radius:").grid(row=16, column=0, sticky="w")
        self.min_radius = Scale(self.control_frame, from_=1, to=20, orient=HORIZONTAL)
        self.min_radius.set(self.MIN_BALL_RADIUS)
        self.min_radius.grid(row=16, column=1, sticky="ew")
        Label(self.control_frame, text="Circularity:").grid(
            row=17, column=0, sticky="w"
        )
        self.circularity = Scale(self.control_frame, from_=0, to=100, orient=HORIZONTAL)
        self.circularity.set(int(self.BALL_CIRCULARITY_THRESHOLD * 100))
        self.circularity.grid(row=17, column=1, sticky="ew")

        # Process button
        Button(
            self.control_frame,
            text="Calculate Measurements",
            command=self.process_measurements,
            bg="lightblue",
            font=("Arial", 10, "bold"),
        ).grid(row=18, column=0, columnspan=2, pady=10, sticky="ew")

    def open_image_file(self):
        self.stop_camera()
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png")]
        )
        if file_path:
            try:
                self.img = cv2.imread(file_path)
                if self.img is None:
                    raise ValueError("Could not read image file")

                self.preview = cv2.resize(
                    self.img,
                    None,
                    fx=self.PREVIEW_SCALE,
                    fy=self.PREVIEW_SCALE,
                    interpolation=cv2.INTER_AREA,
                )

                self.field_pts = []
                self.ball_pt1 = None
                self.ball_detected = False
                self.ball_status.config(text="Ball: Not detected")
                self.corner_listbox.delete(0, END)
                self.capture_btn.config(state=DISABLED)
                self.camera_mode = False

                self.update_display()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open image: {str(e)}")

    def open_camera(self):
        self.stop_camera()
        try:
            self.cap = cv2.VideoCapture(2)
            if not self.cap.isOpened():
                raise ValueError("Could not open camera")

            self.camera_mode = True
            self.capture_btn.config(state=NORMAL)
            self.field_pts = []
            self.ball_pt1 = None
            self.ball_detected = False
            self.ball_status.config(text="Ball: Not detected")
            self.corner_listbox.delete(0, END)

            # Start camera thread
            self.camera_thread = threading.Thread(target=self.update_camera)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            self.root.after(
                1000, self.detect_ball
            )  # Ensure detect_ball runs after camera starts

        except Exception as e:
            messagebox.showerror("Error", f"Could not open camera: {str(e)}")

    def stop_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.camera_mode = False

    def update_camera(self):
        while self.cap is not None and self.cap.isOpened() and self.running:
            ret, frame = self.cap.read()
            if ret:
                self.img = frame.copy()

                # Perform ball detection if in camera mode
                if self.camera_mode:
                    self.detect_balls_in_frame()

                self.preview = cv2.resize(
                    frame,
                    None,
                    fx=self.PREVIEW_SCALE,
                    fy=self.PREVIEW_SCALE,
                    interpolation=cv2.INTER_AREA,
                )

                self.update_display()
            cv2.waitKey(30)

    def detect_balls_in_frame(self):
        if self.img is None or len(self.field_pts) != 4:
            return

        # Create field mask
        mask = np.zeros(self.img.shape[:2], dtype=np.uint8)
        pts = np.array(
            [
                self.field_pts[0],
                self.field_pts[1],
                self.field_pts[3],
                self.field_pts[2],
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [pts], 255)

        # Apply mask to the image
        masked_img = cv2.bitwise_and(self.img, self.img, mask=mask)

        # Enhanced preprocessing for shadow reduction
        lab = cv2.cvtColor(masked_img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # CLAHE for better contrast in shadows
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge((l, a, b))
        enhanced_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        blurred = cv2.GaussianBlur(enhanced_img, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # Adjusted color ranges for bocce balls with stitching
        # color_ranges = {
        #     "white": [
        #         (
        #             np.array([0, 0, 160]),
        #             np.array([180, 40, 255]),
        #         )  # Lower saturation for white
        #     ],
        #     "red": [
        #         (
        #             np.array([0, 100, 50]),
        #             np.array([15, 255, 255]),
        #         ),  # Wider hue range for red
        #         (np.array([160, 100, 50]), np.array([180, 255, 255])),
        #     ],
        #     "blue": [
        #         (
        #             np.array([100, 150, 30]),
        #             np.array([130, 255, 80]),
        #         )  # Lower value (darker)
        #     ],
        # }

        # Create mask using user-defined HSV thresholds
        color_mask = cv2.inRange(hsv, self.WHITE_COLOR_LOWER, self.WHITE_COLOR_UPPER)

        # Apply basic morphology
        kernel = np.ones((3, 3), np.uint8)
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)

        all_detect = []

        # Special processing for each color
        for color_name, ranges in color_mask.items():
            color_mask = np.zeros(masked_img.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                color_mask = cv2.bitwise_or(color_mask, cv2.inRange(hsv, lower, upper))
            2
            # Color-specific morphological operations
            if color_name == "white":
                kernel = np.ones((3, 3), np.uint8)
                color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)
            else:
                kernel = np.ones((5, 5), np.uint8)
                color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
                color_mask = cv2.dilate(color_mask, kernel, iterations=1)

            # Find contours with shadow-tolerant parameters
            contours, _ = cv2.findContours(
                color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 200 < area < 30000:  # Adjusted size range
                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter**2)

                        # Relaxed circularity for stitched balls
                        if circularity > 0.4:
                            (x, y), radius = cv2.minEnclosingCircle(cnt)

                            # Additional check for solidity
                            hull = cv2.convexHull(cnt)
                            hull_area = cv2.contourArea(hull)
                            solidity = float(area) / hull_area if hull_area > 0 else 0

                            if solidity > 0.7:  # Reject very concave shapes
                                x1, y1 = int(x - radius), int(y - radius)
                                x2, y2 = int(x + radius), int(y + radius)

                                # Confidence based on multiple factors
                                confidence = min(
                                    1.0, (circularity * 0.6 + solidity * 0.4)
                                )

                                cls_id = (
                                    1
                                    if color_name == "white"
                                    else (2 if color_name == "red" else 0)
                                )

                                all_detect.append(
                                    {
                                        "bbox": (x1, y1, x2, y2),
                                        "confidence": confidence,
                                        "class": cls_id,
                                        "center": (int(x), int(y)),
                                        "radius": int(radius),
                                        "color": color_name,
                                    }
                                )

        # Rest of your NMS and tracking logic remains the same
        boxes = [
            [x1, y1, x2 - x1, y2 - y1]
            for x1, y1, x2, y2 in (det["bbox"] for det in all_detect)
        ]
        confidences = [det["confidence"] for det in all_detect]

        nms_indices = (
            cv2.dnn.NMSBoxes(boxes, confidences, self.detection_threshold, 0.1)
            if len(boxes) > 0
            else []
        )

        if len(nms_indices) > 0:
            if isinstance(nms_indices, np.ndarray):
                nms_indices = nms_indices.flatten().tolist()
            filtered_detections = [all_detect[i] for i in nms_indices]
        else:
            filtered_detections = []

        self.ball_all = filtered_detections.copy()

        # Visualization with color coding
        output_img = self.img.copy()
        for det in filtered_detections:
            color = (
                (255, 255, 255)
                if det["color"] == "white"
                else (0, 0, 255) if det["color"] == "red" else (255, 0, 0)
            )  # blue

            cv2.circle(output_img, det["center"], det["radius"], color, 2)
            cv2.putText(
                output_img,
                f"{det['color']} {det['confidence']:.2f}",
                (
                    det["center"][0] - det["radius"],
                    det["center"][1] - det["radius"] - 10,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

        # Your existing ball tracking logic
        white_balls = [det for det in filtered_detections if det["class"] == 1]
        if white_balls:
            best_ball = max(white_balls, key=lambda x: x["confidence"])
            self.ball_pt1 = best_ball["center"]
            self.ball_detected = True
            self.ball_status.config(text=f"Ball: Detected at {self.ball_pt1}")
        else:
            self.ball_pt1 = None
            self.ball_detected = False
            self.ball_status.config(text="Ball: Not detected")

        return output_img

    def capture_frame(self):
        if self.camera_mode and self.img is not None:
            self.camera_mode = False
            self.capture_btn.config(state=DISABLED)
            self.update_display()

    def update_display(self):
        if self.img is None:
            return

        # Draw preview with points
        preview_copy = self.preview.copy()
        for i, pt in enumerate(self.field_pts):
            x_prev, y_prev = int(pt[0] * self.PREVIEW_SCALE), int(
                pt[1] * self.PREVIEW_SCALE
            )
            cv2.circle(preview_copy, (x_prev, y_prev), 5, (0, 255, 0), -1)
            cv2.putText(
                preview_copy,
                str(i + 1),
                (x_prev + 10, y_prev + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )

        if self.ball_pt1:
            x_ball, y_ball = int(self.ball_pt1[0] * self.PREVIEW_SCALE), int(
                self.ball_pt1[1] * self.PREVIEW_SCALE
            )
            cv2.circle(preview_copy, (x_ball, y_ball), 5, (0, 0, 255), -1)
            cv2.putText(
                preview_copy,
                "Ball",
                (x_ball + 10, y_ball + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )

        if len(self.ball_all) > 0:
            for det in self.ball_all:
                x1, y1, x2, y2 = det["bbox"]
                x1, y1 = int(x1 * self.PREVIEW_SCALE), int(y1 * self.PREVIEW_SCALE)
                x2, y2 = int(x2 * self.PREVIEW_SCALE), int(y2 * self.PREVIEW_SCALE)
                cv2.rectangle(preview_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
                class_name = ""
                if det["class"] == 0:
                    class_name = "Blue"
                elif det["class"] == 1:
                    class_name = "White"
                elif det["class"] == 2:
                    class_name = "Red"
                cv2.rectangle(preview_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    preview_copy,
                    f"{class_name}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

        # Convert to PhotoImage for display
        preview_rgb = cv2.cvtColor(preview_copy, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(preview_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        self.canvas.config(width=img_pil.width, height=img_pil.height)
        self.canvas.create_image(0, 0, anchor=NW, image=img_tk)
        self.canvas.image = img_tk  # Keep a reference

        # Update threshold display
        self.update_threshold_display()

    def update_thresholds(self, event=None):
        self.WHITE_COLOR_LOWER = np.array(
            [self.lower_h.get(), self.lower_s.get(), self.lower_v.get()], np.uint8
        )

        self.WHITE_COLOR_UPPER = np.array(
            [self.upper_h.get(), self.upper_s.get(), self.upper_v.get()], np.uint8
        )

        self.update_threshold_display()

    def update_threshold_display(self):
        if self.img is None:
            return

        hsv = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, self.WHITE_COLOR_LOWER, self.WHITE_COLOR_UPPER)

        # Resize for display
        thresh_display = cv2.resize(
            thresh_display,
            None,
            fx=self.PREVIEW_SCALE,
            fy=self.PREVIEW_SCALE,
            interpolation=cv2.INTER_NEAREST,
        )

        img_pil = Image.fromarray(thresh_display)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        self.thresh_label.config(
            image=img_tk, width=img_pil.width, height=img_pil.height
        )
        self.thresh_label.image = img_tk  # Keep a reference

    def update_loupe(self, event):
        if self.img is None:
            return

        self.cursor_preview = (event.x, event.y)
        X = int(event.x / self.PREVIEW_SCALE)
        Y = int(event.y / self.PREVIEW_SCALE)

        half = int(self.LOUPE_WIN / (2 * self.LOUPE_SCALE))
        x1, y1 = max(0, X - half), max(0, Y - half)
        x2, y2 = min(self.img.shape[1], X + half), min(self.img.shape[0], Y + half)

        patch = self.img[y1:y2, x1:x2]
        loupe = cv2.resize(
            patch, (self.LOUPE_WIN, self.LOUPE_WIN), interpolation=cv2.INTER_NEAREST
        )

        center = self.LOUPE_WIN // 2
        cv2.circle(loupe, (center, center), self.TARGET_RADIUS, self.TARGET_COLOR, -1)
        cv2.rectangle(
            loupe,
            (0, 0),
            (self.LOUPE_WIN - 1, self.LOUPE_WIN - 1),
            self.LOUPE_BORDER_COLOR,
            self.LOUPE_BORDER,
        )

        loupe_rgb = cv2.cvtColor(loupe, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(loupe_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        self.loupe_label.config(
            image=img_tk, width=img_pil.width, height=img_pil.height
        )
        self.loupe_label.image = img_tk  # Keep a reference

    def add_point(self, event):
        if self.img is None:
            return

        if len(self.field_pts) < 4:
            X = int(event.x / self.PREVIEW_SCALE)
            Y = int(event.y / self.PREVIEW_SCALE)
            self.field_pts.append((X, Y))
            self.corner_listbox.insert(END, f"Corner {len(self.field_pts)}: ({X}, {Y})")
            self.update_display()

        # if len(self.field_pts) == 4:
        #     # Draw the quadrilateral
        #     preview_copy = self.preview.copy()
        #     scaled_pts = [(int(pt[0] * self.PREVIEW_SCALE), int(pt[1] * self.PREVIEW_SCALE)) for pt in self.field_pts]

        #     # 0→1→3→2→0 order
        #     connection_order = [0, 1, 3, 2, 0]
        #     for i in range(len(connection_order)-1):
        #         start = connection_order[i]
        #         end = connection_order[i+1]
        #         cv2.line(preview_copy, scaled_pts[start], scaled_pts[end], (0, 255, 0), 2)

        #     cv2.imshow("Preview", preview_copy)

        #     # Automatically save when 4 points are selected
        #     self.save_quadrilateral()

    def save_quadrilateral(self, output_path="output_quadrilateral.png"):
        if len(self.field_pts) != 4 or self.img is None:
            print("Need exactly 4 points to save quadrilateral")
            return

        # Create a mask for the quadrilateral with your specific point order
        mask = np.zeros(self.img.shape[:2], dtype=np.uint8)

        # Convert points to numpy array in your specific order: 0→1→3→2→0
        pts = np.array(
            [
                self.field_pts[0],  # Point 0
                self.field_pts[1],  # Point 1
                self.field_pts[3],  # Point 3
                self.field_pts[2],  # Point 2
            ],
            dtype=np.int32,
        )

        # Fill the polygon with white (255)
        cv2.fillPoly(mask, [pts], 255)

        # Apply the mask to get just the quadrilateral area
        result = cv2.bitwise_and(self.img, self.img, mask=mask)

        # Get the bounding rectangle of the quadrilateral
        x, y, w, h = cv2.boundingRect(pts)

        # Crop to the bounding rectangle
        cropped = result[y : y + h, x : x + w]

        # Create a transparent version (optional)
        if self.img.shape[2] == 3:  # If original image has no alpha channel
            b, g, r = cv2.split(cropped)
            alpha = mask[y : y + h, x : x + w]  # Use the mask as alpha channel
            transparent = cv2.merge([b, g, r, alpha])
        else:
            transparent = cropped

        # Save the result (both regular and transparent versions)
        cv2.imwrite(output_path, cropped)
        if len(transparent.shape) == 3 and transparent.shape[2] == 4:
            cv2.imwrite(output_path.replace(".png", "_transparent.png"), transparent)

        print(f"Saved quadrilateral image to {output_path}")

    def remove_last_point(self):
        if self.field_pts:
            self.field_pts.pop()
            self.corner_listbox.delete(END)
            self.update_display()

    def clear_points(self):
        self.field_pts = []
        self.corner_listbox.delete(0, END)
        self.update_display()

    def detect_ball(self):
        """Manual trigger for ball detection"""
        if self.img is not None:
            self.detect_balls_in_frame()
            self.update_display()

    def _get_threshold_mask(self, image):
        return cv2.inRange(image, self.WHITE_COLOR_LOWER, self.WHITE_COLOR_UPPER)

    def process_measurements(self):
        if self.img is None:
            messagebox.showwarning("Warning", "Please open an image or camera first")
            return

        if len(self.field_pts) != 4:
            messagebox.showwarning("Warning", "Please mark all 4 field corners")
            return

        # Create perspective transform from field corners to top-down view
        src = np.float32(self.field_pts)
        dst = np.float32(
            [
                [0, 0],
                [0, self.FIELD_H_CM],
                [self.FIELD_W_CM, 0],
                [self.FIELD_W_CM, self.FIELD_H_CM],
            ]
        )
        H = cv2.getPerspectiveTransform(src, dst)

        # Create results window
        result_window = Toplevel(self.root)
        result_window.title("Field Top View")

        # Show warped image (top view)
        warp_w, warp_h = int(self.FIELD_W_CM), int(self.FIELD_H_CM)
        warped = cv2.warpPerspective(self.img, H, (warp_w, warp_h))
        self.top_view = warped
        self.detect_ball()
        # Convert warped image for display
        warped_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(warped_rgb)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        Label(
            result_window, text="Field Top View (1 px = 1 cm)", font=("Arial", 12)
        ).pack()
        warped_label = Label(result_window, image=img_tk)
        warped_label.image = img_tk  # Keep a reference
        warped_label.pack(pady=10)

        Button(result_window, text="Close", command=result_window.destroy).pack(pady=10)

    def on_closing(self):
        self.running = False
        self.stop_camera()
        self.root.destroy()


if __name__ == "__main__":
    root = Tk()
    app = FieldMeasureApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

# --------------- PLC Communication ---------------------
# lib for connecting and editing PLC with Ethernet SLMP
# setting up
# MyPLC = pymcprotocol.Type3E()
# MyPLC.setaccessopt(commtype="binary")
# MyPLC.connect(ip="192.168.0.200", port=2001)

# if pymc3e._is_connected:
#     cpu_type, cpu_code = pymc3e.read_cputype()
#     print(cpu_type, cpu_code)

# """ e.g. sending data to PLC
# MyPLC.randomwrite(word_device=["DXXX","DXXX"],word_values=[a,b])
# """
# -------------------------------------------------------
