import cv2
import numpy as np
import math
from tkinter import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time


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
    WHITE_COLOR_LOWER = np.array([0, 0, 160], np.uint8)
    WHITE_COLOR_UPPER = np.array([255, 255, 255], np.uint8)
    RED_COLOR_LOWER = np.array([0, 100, 50], np.uint8)
    RED_COLOR_UPPER = np.array([15, 255, 255], np.uint8)
    BLUE_COLOR_LOWER = np.array([100, 150, 30], np.uint8)
    BLUE_COLOR_UPPER = np.array([130, 255, 80], np.uint8)
    MIN_BALL_RADIUS = 12  # Minimum radius (in pixels) to consider a ball
    PREVIEW_SCALE = 0.2  # main preview size

    # --------------------------------

    def __init__(self, root):
        self.root = root
        self.root.title("Field Measurement Tool")
        self.color_range = []
        self.status_click_color = False
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
        self.BALL_CIRCULARITY_THRESHOLD = 0.50  # Minimum circularity to consider a ball
        self.BALL_SOLIDITY_THRESHOLD = 0.70

        # Create UI
        # self.yolo_model = YOLO('best.pt')  # Make sure the model file is in the correct path
        self.detection_threshold = 0.01

        # Create UI
        self.create_widgets()
        # Start camera thread if in camera mode
        self.camera_thread = None
        # Call detect_ball every 5 seconds
        self.detect_ball_timer()

    def detect_ball_timer(self):
        if self.running:
            self.detect_ball()
            self.process_measurements()
            self.root.after(3000, self.detect_ball_timer)

    def open_hsv_popup(self):
        # Create a new popup window
        hsv_popup = Toplevel(self.root)
        hsv_popup.title("Adjust HSV Thresholds")
        hsv_popup.geometry("500x400")  # Adjust the size to fit all sliders

        # White HSV Controls
        Label(hsv_popup, text="White HSV:").grid(row=0, column=0, columnspan=2, pady=5)
        Label(hsv_popup, text="Lower").grid(row=1, column=0)
        Label(hsv_popup, text="Upper").grid(row=1, column=1)

        self.white_lower_h = Scale(
            hsv_popup,
            from_=0,
            to=180,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.white_lower_h.set(0)
        self.white_lower_h.grid(row=2, column=0, padx=5, pady=5)

        self.white_upper_h = Scale(
            hsv_popup,
            from_=0,
            to=180,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.white_upper_h.set(180)
        self.white_upper_h.grid(row=2, column=1, padx=5, pady=5)

        self.white_lower_s = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.white_lower_s.set(0)
        self.white_lower_s.grid(row=3, column=0, padx=5, pady=5)

        self.white_upper_s = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.white_upper_s.set(40)
        self.white_upper_s.grid(row=3, column=1, padx=5, pady=5)

        self.white_lower_v = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.white_lower_v.set(160)
        self.white_lower_v.grid(row=4, column=0, padx=5, pady=5)

        self.white_upper_v = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.white_upper_v.set(255)
        self.white_upper_v.grid(row=4, column=1, padx=5, pady=5)

        # Red HSV Controls (Move to the right of White HSV)
        Label(hsv_popup, text="Red HSV:").grid(row=0, column=2, columnspan=2, pady=5)
        Label(hsv_popup, text="Lower").grid(row=1, column=2)
        Label(hsv_popup, text="Upper").grid(row=1, column=3)

        self.red_lower_h = Scale(
            hsv_popup,
            from_=0,
            to=180,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.red_lower_h.set(0)
        self.red_lower_h.grid(row=2, column=2, padx=5, pady=5)

        self.red_upper_h = Scale(
            hsv_popup,
            from_=0,
            to=180,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.red_upper_h.set(15)
        self.red_upper_h.grid(row=2, column=3, padx=5, pady=5)

        self.red_lower_s = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.red_lower_s.set(100)
        self.red_lower_s.grid(row=3, column=2, padx=5, pady=5)

        self.red_upper_s = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.red_upper_s.set(255)
        self.red_upper_s.grid(row=3, column=3, padx=5, pady=5)

        self.red_lower_v = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.red_lower_v.set(50)
        self.red_lower_v.grid(row=4, column=2, padx=5, pady=5)

        self.red_upper_v = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.red_upper_v.set(255)
        self.red_upper_v.grid(row=4, column=3, padx=5, pady=5)

        # Blue HSV Controls (Below White HSV)
        Label(hsv_popup, text="Blue HSV:").grid(row=5, column=0, columnspan=2, pady=5)
        self.blue_lower_h = Scale(
            hsv_popup,
            from_=0,
            to=180,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.blue_lower_h.set(100)
        self.blue_lower_h.grid(row=6, column=0, padx=5, pady=5)

        self.blue_upper_h = Scale(
            hsv_popup,
            from_=0,
            to=180,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.blue_upper_h.set(130)
        self.blue_upper_h.grid(row=6, column=1, padx=5, pady=5)

        self.blue_lower_s = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.blue_lower_s.set(150)
        self.blue_lower_s.grid(row=7, column=0, padx=5, pady=5)

        self.blue_upper_s = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.blue_upper_s.set(255)
        self.blue_upper_s.grid(row=7, column=1, padx=5, pady=5)

        self.blue_lower_v = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.blue_lower_v.set(30)
        self.blue_lower_v.grid(row=8, column=0, padx=5, pady=5)

        self.blue_upper_v = Scale(
            hsv_popup,
            from_=0,
            to=255,
            orient=HORIZONTAL,
            command=self.update_thresholds,
        )
        self.blue_upper_v.set(80)
        self.blue_upper_v.grid(row=8, column=1, padx=5, pady=5)

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

        Button(
            self.control_frame,
            text="Adjust HSV Thresholds",
            command=self.open_hsv_popup,
            bg="lightblue",
            font=("Arial", 10, "bold"),
        ).grid(row=20, column=0, columnspan=2, pady=10, sticky="ew")

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

        # Ball detection parameters
        Label(
            self.control_frame, text="Detection Params", font=("Arial", 12, "bold")
        ).grid(row=15, column=0, columnspan=2, pady=5)

        Label(self.control_frame, text="solidity:").grid(row=16, column=0, sticky="w")
        self.solidity_scale_widget = Scale(
            self.control_frame, from_=0, to=100, orient=HORIZONTAL
        )
        self.solidity_scale_widget.set(int(self.BALL_SOLIDITY_THRESHOLD * 100))
        self.solidity_scale_widget.grid(row=16, column=1, sticky="ew")
        self.solidity_scale_widget.bind(
            "<ButtonRelease-1>", self.update_solidity
        )  # อัปเดตเมื่อปล่อยเมาส์

        Label(self.control_frame, text="Circularity:").grid(
            row=17, column=0, sticky="w"
        )
        self.circularity_scale_widget = Scale(
            self.control_frame, from_=0, to=100, orient=HORIZONTAL
        )
        self.circularity_scale_widget.set(int(self.BALL_CIRCULARITY_THRESHOLD * 100))
        self.circularity_scale_widget.grid(row=17, column=1, sticky="ew")
        self.circularity_scale_widget.bind("<ButtonRelease-1>", self.update_circularity)

        # Process button
        Button(
            self.control_frame,
            text="Calculate Measurements",
            command=self.process_measurements,
            bg="lightblue",
            font=("Arial", 10, "bold"),
        ).grid(row=18, column=0, columnspan=2, pady=10, sticky="ew")
        Button(
            self.control_frame,
            text="Click Color ",
            command=self.pick_color,
            bg="lightblue",
            font=("Arial", 10, "bold"),
        ).grid(row=19, column=0, columnspan=2, pady=10, sticky="ew")

    def update_solidity(self, event=None):
        print("update_solidity called")
        self.BALL_SOLIDITY_THRESHOLD = self.solidity_scale_widget.get() / 100.0
        print(f"Updated Solidity Threshold: {self.BALL_SOLIDITY_THRESHOLD}")

    def update_circularity(self, event=None):
        print("update_circularity called")
        self.BALL_CIRCULARITY_THRESHOLD = self.circularity_scale_widget.get() / 100.0
        print(f"Updated Circularity Threshold: {self.BALL_CIRCULARITY_THRESHOLD}")

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

    def pick_color(self):
        if self.img is None:
            messagebox.showwarning("Warning", "Please open an image or camera first")
            return

        self.status_click_color = True
        self.color_range = []  # Reset color list
        self.canvas.bind("<Button-1>", self.get_color)  # Bind click to image
        print("Click on image to pick 3 colors...")

    def get_color(self, event):
        if not self.status_click_color:
            return

        # Convert canvas coordinates to image coordinates (if scaled, adjust here)
        x, y = event.x, event.y
        if x >= self.img.shape[1] or y >= self.img.shape[0]:
            return

        # Get color from image
        b, g, r = self.img[y, x]
        color = (r, g, b)  # RGB format
        lower_bound = np.array([b - 10, g - 10, r - 10], dtype=np.uint8)
        upper_bound = np.array([b + 10, g + 10, r + 10], dtype=np.uint8)
        color_range = (lower_bound, upper_bound)
        if len(self.color_range) < 3:
            self.color_range.append(color)
            print(f"Picked color {len(self.color_range)}: {color}")

        if len(self.color_range) == 3:
            print("✅ Finished picking 3 colors:", self.color_range)
            self.status_click_color = False
            self.canvas.unbind("<Button-1>")

    def open_camera(self):
        self.stop_camera()
        try:
            self.cap = cv2.VideoCapture(1)
            if not self.cap.isOpened():
                raise ValueError("Could not open camera")

            self.camera_mode = True
            self.capture_btn.config(state=NORMAL)
            self.field_pts = []
            self.ball_pt1 = None
            self.ball_detected = False
            self.ball_status.config(text="Ball: Not detected")
            self.corner_listbox.delete(0, END)

            self.update_camera()  # Start the update loop

        except Exception as e:
            messagebox.showerror("Error", f"Could not open camera: {str(e)}")

    def show_white_ball_mask(self):
        if self.img is None:
            return

        # แปลงภาพเป็น HSV
        hsv = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)

        # สร้าง Mask สำหรับลูกบอลสีขาว
        white_mask = cv2.inRange(hsv, self.WHITE_COLOR_LOWER, self.WHITE_COLOR_UPPER)

    def stop_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.camera_mode = False

    def update_camera(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.img = frame.copy()
                self.preview = cv2.resize(
                    frame,
                    None,
                    fx=self.PREVIEW_SCALE,
                    fy=self.PREVIEW_SCALE,
                    interpolation=cv2.INTER_AREA,
                )

                if self.camera_mode:
                    self.detect_balls_in_frame()

                self.update_display()

        self.root.after(30, self.update_camera)  # Schedule next frame

    def detect_balls_in_frame(self):
        hsv = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)
        white_mask = cv2.inRange(hsv, self.WHITE_COLOR_LOWER, self.WHITE_COLOR_UPPER)
        scale_percent = 50  # ลดขนาดลง 50%
        width = int(white_mask.shape[1] * scale_percent / 100)
        height = int(white_mask.shape[0] * scale_percent / 100)
        resized_mask = cv2.resize(
            white_mask, (width, height), interpolation=cv2.INTER_AREA
        )
        cv2.imshow("White Mask", resized_mask)

        if self.img is None or len(self.field_pts) != 4:
            return

        # ตรวจจับลูกบอลสีขาว
        white_balls = [det for det in self.ball_all if det["class"] == 1]
        if white_balls:
            best_ball = max(white_balls, key=lambda x: x["confidence"])
            self.ball_pt1 = best_ball["center"]
            self.ball_detected = True
            self.ball_status.config(text=f"Ball: Detected at {self.ball_pt1}")

        else:
            self.ball_pt1 = None
            self.ball_detected = False
            self.ball_status.config(text="Ball: Not detected")

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
        # Display the HSV image for debugging

        # Adjusted color ranges for bocce balls with stitching
        color_ranges = {
            "white": [
                (
                    np.array([0, 0, 160]),
                    np.array([180, 40, 255]),
                )  # Lower saturation for white
            ],
            "red": [
                (
                    np.array([0, 100, 50]),
                    np.array([15, 255, 255]),
                ),  # Wider hue range for red
                (np.array([160, 100, 50]), np.array([180, 255, 255])),
            ],
            "blue": [
                (
                    np.array([100, 150, 30]),
                    np.array([130, 255, 80]),
                )  # Lower value (darker)
            ],
        }

        all_detect = []
        print(self.BALL_CIRCULARITY_THRESHOLD)
        print(self.BALL_SOLIDITY_THRESHOLD)
        # Special processing for each color
        for color_name, ranges in color_ranges.items():
            color_mask = np.zeros(masked_img.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                img_range = cv2.inRange(hsv, lower, upper)
                # cv2.imshow(f"{color_name} mask", img_range)  # Debugging line
                color_mask = cv2.bitwise_or(color_mask, cv2.inRange(hsv, lower, upper))
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
                if 200 < area < 1500:  # Adjusted size range30000
                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter**2)

                        # Relaxed circularity for stitched balls
                        if circularity > self.BALL_CIRCULARITY_THRESHOLD:
                            (x, y), radius = cv2.minEnclosingCircle(cnt)

                            # Additional check for solidity
                            hull = cv2.convexHull(cnt)
                            hull_area = cv2.contourArea(hull)
                            solidity = float(area) / hull_area if hull_area > 0 else 0

                            if (
                                solidity > self.BALL_SOLIDITY_THRESHOLD
                            ):  # Reject very concave shapes
                                x1, y1 = int(x - radius), int(y - radius)
                                x2, y2 = int(x + radius), int(y + radius)

                                # Confidence based on multiple factors
                                confidence = min(
                                    1.0, (circularity * 0.7 + solidity * 0.3)
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

        print(all_detect)
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
        white_balls = [det for det in filtered_detections if det["class"] == 1]
        if not white_balls:
            # ✅ เพิ่มตรงนี้: ใช้ Grayscale ช่วยหาบอลขาวแทน
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)

            # ปรับค่าความสว่างเล็กน้อย
            gray = cv2.equalizeHist(gray)

            # Threshold เพื่อให้ลูกบอลขาวเด่นขึ้น
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

            # หา contour จาก mask ขาวดำ
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 150 < area < 1500:  # ปรับช่วงให้เหมาะกับบอล
                    perimeter = cv2.arcLength(cnt, True)
                    circularity = (
                        4 * np.pi * area / (perimeter**2) if perimeter != 0 else 0
                    )

                    if circularity > self.BALL_CIRCULARITY_THRESHOLD:
                        (x, y), radius = cv2.minEnclosingCircle(cnt)
                        hull = cv2.convexHull(cnt)
                        hull_area = cv2.contourArea(hull)
                        solidity = area / hull_area if hull_area > 0 else 0

                        if solidity > self.BALL_SOLIDITY_THRESHOLD:
                            # บันทึกบอลขาวที่เจอจากขาวดำ
                            self.ball_pt1 = (int(x), int(y))
                            self.ball_detected = True
                            self.ball_status.config(
                                text=f"Ball (gray): {self.ball_pt1}"
                            )
                            break  # เอาลูกแรกที่เจอพอ

        # Visualization with color coding
        output_img = self.img.copy()
        for det in filtered_detections:
            color = (
                (255, 255, 255)
                if det["color"] == "white"
                else (0, 0, 255) if det["color"] == "red" else (255, 0, 0)  # blue
            )

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
        # Update HSV ranges for White
        self.WHITE_COLOR_LOWER = np.array(
            [
                self.white_lower_h.get(),
                self.white_lower_s.get(),
                self.white_lower_v.get(),
            ],
            np.uint8,
        )
        self.WHITE_COLOR_UPPER = np.array(
            [
                self.white_upper_h.get(),
                self.white_upper_s.get(),
                self.white_upper_v.get(),
            ],
            np.uint8,
        )

        # Update HSV ranges for Blue
        self.BLUE_COLOR_LOWER = np.array(
            [self.blue_lower_h.get(), self.blue_lower_s.get(), self.blue_lower_v.get()],
            np.uint8,
        )
        self.BLUE_COLOR_UPPER = np.array(
            [self.blue_upper_h.get(), self.blue_upper_s.get(), self.blue_upper_v.get()],
            np.uint8,
        )

        # Update HSV ranges for Red
        self.RED_COLOR_LOWER = np.array(
            [self.red_lower_h.get(), self.red_lower_s.get(), self.red_lower_v.get()],
            np.uint8,
        )
        self.RED_COLOR_UPPER = np.array(
            [self.red_upper_h.get(), self.red_upper_s.get(), self.red_upper_v.get()],
            np.uint8,
        )

        self.update_threshold_display()

    def update_threshold_display(self):
        if self.img is None:
            return

        # แปลงภาพต้นฉบับเป็น HSV
        hsv_img = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)

        # สร้าง Mask สำหรับแต่ละสี
        white_mask = cv2.inRange(
            hsv_img, self.WHITE_COLOR_LOWER, self.WHITE_COLOR_UPPER
        )
        red_mask_1 = cv2.inRange(hsv_img, self.RED_COLOR_LOWER, self.RED_COLOR_UPPER)
        red_mask_2 = cv2.inRange(
            hsv_img, np.array([160, 100, 50]), np.array([180, 255, 255])
        )
        red_mask = cv2.bitwise_or(red_mask_1, red_mask_2)
        blue_mask = cv2.inRange(hsv_img, self.BLUE_COLOR_LOWER, self.BLUE_COLOR_UPPER)

        # รวม Mask ทั้งหมด
        combined_mask = cv2.bitwise_or(white_mask, cv2.bitwise_or(red_mask, blue_mask))

        # แปลง Mask เป็นภาพสี HSV
        hsv_display = cv2.bitwise_and(hsv_img, hsv_img, mask=combined_mask)

        # แปลงภาพ HSV เป็น RGB เพื่อแสดงใน Tkinter
        rgb_display = cv2.cvtColor(hsv_display, cv2.COLOR_HSV2RGB)

        # Resize ภาพสำหรับการแสดงผล
        resized_display = cv2.resize(
            rgb_display,
            None,
            fx=self.PREVIEW_SCALE,
            fy=self.PREVIEW_SCALE,
            interpolation=cv2.INTER_NEAREST,
        )

        # แปลงภาพเป็นรูปแบบที่รองรับโดย Tkinter
        img_pil = Image.fromarray(resized_display)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        # อัปเดต Threshold Display ใน UI
        self.thresh_label.config(
            image=img_tk, width=img_pil.width, height=img_pil.height
        )
        self.thresh_label.image = img_tk  # เก็บอ้างอิงเพื่อป้องกันการถูกลบโดย garbage collector

    def update_loupe(self, event):  # ภาพขยายตอนที่เม้าชี้
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
            self.detect_ball_timer()

    # def save_quadrilateral(self, output_path="output_quadrilateral.png"):
    #     if len(self.field_pts) != 4 or self.img is None:
    #         print("Need exactly 4 points to save quadrilateral")
    #         return

    #     # Create a mask for the quadrilateral with your specific point order
    #     mask = np.zeros(self.img.shape[:2], dtype=np.uint8)

    #     # Convert points to numpy array in your specific order: 0→1→3→2→0
    #     pts = np.array(
    #         [
    #             self.field_pts[0],  # Point 0
    #             self.field_pts[1],  # Point 1
    #             self.field_pts[3],  # Point 3
    #             self.field_pts[2],  # Point 2
    #         ],
    #         dtype=np.int32,
    #     )

    #     # Fill the polygon with white (255)
    #     cv2.fillPoly(mask, [pts], 255)

    #     # Apply the mask to get just the quadrilateral area
    #     result = cv2.bitwise_and(self.img, self.img, mask=mask)

    #     # Get the bounding rectangle of the quadrilateral
    #     x, y, w, h = cv2.boundingRect(pts)

    #     # Crop to the bounding rectangle
    #     cropped = result[y : y + h, x : x + w]

    #     # Create a transparent version (optional)
    #     if self.img.shape[2] == 3:  # If original image has no alpha channel
    #         b, g, r = cv2.split(cropped)
    #         alpha = mask[y : y + h, x : x + w]  # Use the mask as alpha channel
    #         transparent = cv2.merge([b, g, r, alpha])
    #     else:
    #         transparent = cropped

    #     # Save the result (both regular and transparent versions)
    #     cv2.imwrite(output_path, cropped)
    #     if len(transparent.shape) == 3 and transparent.shape[2] == 4:
    #         cv2.imwrite(output_path.replace(".png", "_transparent.png"), transparent)

    #     print(f"Saved quadrilateral image to {output_path}")

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
        return cv2.inRange(image, self.BLUE_COLOR_LOWER, self.BLUE_COLOR_UPPER)
        return cv2.inRange(image, self.RED_COLOR_LOWER, self.RED_COLOR_UPPER)

    def process_measurements(self):
        print("process_measurements called")

        src = np.float32(self.field_pts)
        dst = np.float32(
            [
                [0, 0],
                [0, self.FIELD_H_CM],
                [self.FIELD_W_CM, 0],
                [self.FIELD_W_CM, self.FIELD_H_CM],
            ]
        )

        if len(self.field_pts) == 4 and self.ball_pt1:
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
            self.ball_pt1 = (self.ball_pt1[0], self.ball_pt1[1] + 5)
            ball1 = np.float32([self.ball_pt1]).reshape(-1, 1, 2)
            x1_cm, y1_cm = cv2.perspectiveTransform(ball1, H)[0, 0]
            print(f"Ball 1 → ({x1_cm:.1f} cm, {y1_cm:.1f} cm)")

            x2_cm, y2_cm = 300.0, 750.0
            delta_x = x2_cm - x1_cm
            delta_y = y2_cm - y1_cm
            distance_cm = math.sqrt(delta_x**2 + delta_y**2)
            print(f"(X ,Y): {x1_cm:.1f} cm , {distance_cm:.1f} cm")

            angle_radians = math.atan2(delta_x, delta_y)
            angle_degrees = math.degrees(angle_radians)
            if angle_degrees < 0:
                angle_degrees += 360
            print(
                f"Angle of distance relative to vertical axis: {angle_degrees:.2f} degrees"
            )

    def on_closing(self):
        self.running = False
        self.stop_camera()
        self.root.destroy()


if __name__ == "__main__":
    root = Tk()
    app = FieldMeasureApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
