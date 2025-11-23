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

        # Distance tracking variables
        self.distance_label = None
        self.last_distance = None

        # Create UI
        self.yolo_model = YOLO("best.pt")
        self.detection_threshold = 0.01

        self.create_widgets()

        # Start distance update loop
        self.update_distance_loop()

    def create_widgets(self):
        # ... (โค้ดเดิม)

        # Add distance display
        Label(self.control_frame, text="Distance", font=("Arial", 12, "bold")).grid(
            row=19, column=0, columnspan=2, pady=5
        )
        self.distance_label = Label(self.control_frame, text="Distance: N/A")
        self.distance_label.grid(row=20, column=0, columnspan=2, pady=2)

    def update_distance_loop(self):
        """Update distance every 5 seconds."""
        if self.ball_pt1 and len(self.field_pts) == 4:
            try:
                # Calculate distance from the first corner to the detected ball
                x1, y1 = self.field_pts[0]
                x2, y2 = self.ball_pt1
                distance = self.CalculateDistance(x1, y1, x2, y2)
                self.distance_label.config(text=f"Distance: {distance:.2f} cm")
            except Exception as e:
                self.distance_label.config(text="Distance: Error")
                print(f"Error calculating distance: {e}")
        else:
            self.distance_label.config(text="Distance: N/A")

        # Schedule the next update
        self.root.after(5000, self.update_distance_loop)

    def CalculateDistance(self, x1, y1, x2, y2):
        """Calculate the distance between two points in cm using perspective transform."""
        if len(self.field_pts) != 4:
            raise ValueError("Field corners must be defined to calculate distance.")

        # Create perspective transform matrix
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

        # Transform points to top-down view
        points = np.array([[x1, y1], [x2, y2]], dtype=np.float32).reshape(-1, 1, 2)
        transformed_points = cv2.perspectiveTransform(points, H)

        # Extract transformed coordinates
        x1_cm, y1_cm = transformed_points[0][0]
        x2_cm, y2_cm = transformed_points[1][0]

        # Calculate the Euclidean distance in cm
        distance = math.sqrt((x2_cm - x1_cm) ** 2 + (y2_cm - y1_cm) ** 2)
        return distance