import tkinter as tk
from PIL import Image, ImageTk
import os
import math
import numpy as np
import cv2


class DraggableDot:
    def __init__(self, canvas, x, y, color, radius=7):
        self.canvas = canvas
        self.radius = radius
        self.color = color
        self.dot = canvas.create_oval(x-radius, y-radius, x+radius, y+radius,fill=color, outline="black", tags="dot")
        self.canvas.tag_bind(self.dot, "<Button-1>", self.on_press)
        self.canvas.tag_bind(self.dot, "<B1-Motion>", self.on_drag)

    def on_press(self, event):
        self._x = event.x
        self._y = event.y

    def on_drag(self, event):
        dx = event.x - self._x
        dy = event.y - self._y
        self.canvas.move(self.dot, dx, dy)
        self._x = event.x
        self._y = event.y

class ImageWithDotsApp:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title("Image with Draggable Dots")

        try:
            self.image = Image.open(image_path)
            self.tk_image = ImageTk.PhotoImage(self.image)
        except Exception as e:
            print(f"Error loading image: {e}")
            self.root.destroy()
            return

        self.canvas = tk.Canvas(root, width=self.tk_image.width(), height=self.tk_image.height())
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        width, height = self.tk_image.width(), self.tk_image.height()
        self.dots = {
            "dot1": DraggableDot(self.canvas, width//4, height//4, "red"),
            "dot2": DraggableDot(self.canvas, width*3//4, height//4, "red"),
            "dot3": DraggableDot(self.canvas, width//4, height*3//4, "red"),
            "dot4": DraggableDot(self.canvas, width*3//4, height*3//4, "red"),
            "dot5": DraggableDot(self.canvas, width//2, height//2, "white"),
        }

        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        self.dist_btn = tk.Button(button_frame, text="Calculate Distances and Scale", command=self.calculate_distances)
        self.dist_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = tk.Button(button_frame, text="Clear Line", command=self.ClearLines)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Add this in the __init__ method of ImageWithDotsApp, inside button_frame
        self.topview_btn = tk.Button(button_frame, text="Show Top View", command=self.show_top_view)
        self.topview_btn.pack(side=tk.LEFT, padx=5)
        
    def show_top_view(self):
        # Get the coordinates of the four corner dots
        src_points = [
            self.get_center(self.dots["dot1"]),
            self.get_center(self.dots["dot2"]),
            self.get_center(self.dots["dot3"]),
            self.get_center(self.dots["dot4"]),
        ]
        
        # Get dot5 position
        ball_px = np.float32([self.get_center(self.dots["dot5"])])
        
        transformer = TopViewTransformer()
        transformer.point(src_points, dst_size=(800, 600))
        
        # Use the original image path
        original_image_path = r"/Users/nattavipolboonsangchaitawat/Documents/lab/plc/img_test_copy/20250424_151400.jpg"
        frame = cv2.imread(original_image_path)
        
        if frame is None:
            print("Error: Could not load the original image")
            return
        
        # Transform the image and the dot5 position
        top_view_image = transformer.transform(frame)
        ball_real = transformer.transform_point(ball_px)
        
        # Calculate distances between corners
        transformed_corners = transformer.transform_points(np.float32(src_points))
        
        # Get coordinates as simple tuples
        tl = transformed_corners[0][0]  # top-left
        tr = transformed_corners[1][0]  # top-right
        bl = transformed_corners[2][0]  # bottom-left
        br = transformed_corners[3][0]  # bottom-right
        print(f"Transformed corners: {tl}, {tr}, {bl}, {br}")
        
        # Draw distances on the image
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        color = (0, 0, 255)  # Red
        thickness = 2
        
        mid_top = self.calculate_fomula_nonselft( tl , tr)
        print( "midtop : " ,mid_top)
        mid_bottom = self.calculate_fomula_nonselft( bl , br)
        print( "mid_bottom : " ,mid_bottom)
        mid_left = self.calculate_fomula_nonselft( tl , bl)
        print( "mid_left : " ,mid_left)
        mid_right =  self.calculate_fomula_nonselft( tr , br)
        print( "mid_right : " ,mid_right)

        y_ratio = 5/((mid_left +mid_right)/2)
        x_ratio = 4/((mid_bottom + mid_top)/2)
        print(y_ratio)
        print(x_ratio)
        # Draw dot5 position
        if ball_real is not None:
            x, y = ball_real[0][0]
            # Calculate distance from dot5 to the left border (x-axis)
            distance_to_left_border = x * x_ratio
            cv2.putText(top_view_image, f"Left Border: {distance_to_left_border:.2f} m", 
                        (int(x) - 100, int(y)), font, scale, color, thickness)

            # Calculate distance from dot5 to the top border (y-axis)
            distance_to_top_border = y * y_ratio
            cv2.putText(top_view_image, f"Top Border: {distance_to_top_border:.2f} m", 
                        (int(x), int(y) - 20), font, scale, color, thickness)
            # cv2.circle(top_view_image, (int(x), int(y)), 10, (0, 255, 0), -1)  # Green dot
            # cv2.putText(top_view_image, f"Dot5: ({x:.1f}, {y:.1f})", 
            #         (int(x) + 15, int(y)), font, scale, (0, 255, 0), thickness)
            print(f"ball_real : {x:.1f}, {y:.1f}")
        cv2.imshow("Top View", top_view_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def ClearLines(self):
        # ลบเส้นเก่าถ้ามี
        self.canvas.delete("line")
        # ลบข้อความเก่าถ้ามี
        self.canvas.delete("text")
        self.canvas.delete("intersection")
        for widget in self.root.pack_slaves():
            if isinstance(widget, tk.Label):
                widget.destroy()
        # ลบจุดตัดเก่าถ้ามี

    def get_center(self, dot):
        coords = self.canvas.coords(dot.dot)
        return (coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2

    def calculate_distance(self, dot1, dot2):
        x1, y1 = self.get_center(dot1)
        x2, y2 = self.get_center(dot2)
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def calculate_fomula(self, dot1, dot2):
        x1, y1 = self.get_center(dot1)
        x2, y2 = self.get_center(dot2)
        # คำนวณระยะทางจริงระหว่างจุดที่รู้
        dist_1_2 = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        print(f"Distance between dot1 and dot2: {dist_1_2:.2f} px")
        return dist_1_2
    
    def calculate_fomula_nonselft(self, dot1, dot2):
        x1, y1 = dot1[0], dot1[1]
        x2, y2 = dot2[0], dot2[1]
        # คำนวณระยะทางจริงระหว่างจุดที่รู้
        dist_1_2 = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        print(f"Distance between dot1 and dot2: {dist_1_2:.2f} px")
        return dist_1_2


    def draw_lines_between_dots(self):
        # วาดเส้นสีเหลืองตามลำดับที่กำหนด
        yellow_lines = [("dot1", "dot2"), ("dot2", "dot4"), ("dot1", "dot3"), ("dot3", "dot4")]
        for name1, name2 in yellow_lines:
            dot1 = self.dots[name1]
            dot2 = self.dots[name2]
            x1, y1 = self.get_center(dot1)
            x2, y2 = self.get_center(dot2)
            # วาดเส้นระหว่าง dot1 และ dot2
            distance = self.calculate_fomula(dot1, dot2)
            self.canvas.create_text((x1+x2)/2, (y1+y2)/2-45, text=f"{distance:.2f} px", fill="black", tags="text")
            self.canvas.create_line(x1, y1, x2, y2, fill="yellow", width=2, tags="line")

        # Get center of dot5
        x5, y5 = self.get_center(self.dots["dot5"])
        marked = []

        # === หา intersection กับเส้นสีเหลืองทั้งหมด ===
        intersections_x = []
        intersections_y = []

        for name1, name2 in yellow_lines:
            d1 = self.dots[name1]
            d2 = self.dots[name2]
            x1, y1 = self.get_center(d1)
            x2, y2 = self.get_center(d2)

            # เส้นแนว X จาก dot5
            inter_x = self.get_intersection(x1, y1, x2, y2, 0, y5, self.canvas.winfo_width(), y5)
            if inter_x:
                intersections_x.append(inter_x)

            # เส้นแนว Y จาก dot5
            inter_y = self.get_intersection(x1, y1, x2, y2, x5, 0, x5, self.canvas.winfo_height())
            if inter_y:
                intersections_y.append(inter_y)

        # === หาจุดตัดที่ใกล้ที่สุดจาก dot5 ===
        # แนว X
        left = [pt for pt in intersections_x if pt[0] < x5]
        right = [pt for pt in intersections_x if pt[0] > x5]
        closest_left = max(left, key=lambda p: p[0], default=None)
        closest_right = min(right, key=lambda p: p[0], default=None)
       
        # แนว Y
        above = [pt for pt in intersections_y if pt[1] < y5]
        below = [pt for pt in intersections_y if pt[1] > y5]
        closest_above = max(above, key=lambda p: p[1], default=None)
        closest_below = min(below, key=lambda p: p[1], default=None)

        for pt in [closest_left, closest_right, closest_above, closest_below]:
            if pt:
                r = 5  # รัศมีของวงกลม
                self.canvas.create_oval(pt[0]-r, pt[1]-r, pt[0]+r, pt[1]+r,
                                        fill="green", outline="black", tags="intersection")
                marked.append(pt)
                self.canvas.create_text(pt[0], pt[1]-10, text=f"({pt[0]:.2f}, {pt[1]:.2f})", fill="black", tags="text")
                print(f"Intersection point: ({pt[0]:.2f}, {pt[1]:.2f})")

        # === วาดเส้น cyan แนว X ===
        if closest_left:
            self.canvas.create_line(x5, y5, closest_left[0], y5, fill="cyan", dash=(4, 2), width=2, tags="line")
        if closest_right:
            self.canvas.create_line(x5, y5, closest_right[0], y5, fill="cyan", dash=(4, 2), width=2, tags="line")
        distance_x = None
        if closest_left and closest_right:
            distance_x = abs(closest_right[0] - closest_left[0])
            print(f"Distance X: {distance_x:.2f} px")
            self.canvas.create_text((closest_left[0] + closest_right[0]) / 2, y5 - 20,
                        text=f"Distance X: {distance_x:.2f} px", fill="blue", tags="text")
            
        # === แสดงผลระยะทางและอัตราส่วน X ===
        self.text_show = tk.Label(self.root, text=f"Distance X px : {distance_x:.2f} px", bg="white", fg="black")
        self.text_show.pack(pady=10)
        ratio = 4.0000/distance_x
        self.text_show = tk.Label(self.root, text=f"Ratio X m : {ratio:.6f} m", bg="white", fg="black")
        self.text_show.pack(pady=10)
        # Calculate using formula with closest_left
        if closest_left:
            formula_result = ratio * abs(x5 - closest_left[0])
            self.text_show = tk.Label(self.root, text=f"Formula Result (Closest Left): {formula_result:.6f} m", bg="white", fg="black")
            self.text_show.pack(pady=10)
        # === วาดเส้น cyan แนว Y ===
        if closest_above:
            self.canvas.create_line(x5, y5, x5, closest_above[1], fill="cyan", dash=(4, 2), width=2, tags="line")
        if closest_below:
            self.canvas.create_line(x5, y5, x5, closest_below[1], fill="cyan", dash=(4, 2), width=2, tags="line")


        # === แสดงผลระยะทางและอัตราส่วน Y ===
        distance_y = None
        distance_y = self.calculate_fomula(self.dots["dot1"], self.dots["dot3"]) + self.calculate_fomula(self.dots["dot2"], self.dots["dot4"])
        distance_y = distance_y / 2
        print(f"Distance Y: {distance_y:.2f} px")
        self.canvas.create_text(x5 + 20, (closest_above[1] + closest_below[1]) / 2,
                        text=f"Distance Y: {distance_y:.2f} px", fill="blue", tags="text")
        self.text_show = tk.Label(self.root, text=f"Distance Y px : {distance_y:.2f} px", bg="white", fg="black")
        self.text_show.pack(pady=10)

        # num_above = self.calculate_fomula_nonselft(closest_below, closest_above)
        # print(f"Distance Y: {num_above:.2f} px")
        ratio = 7.5000/distance_y
        self.text_show = tk.Label(self.root, text=f"Ratio Y m : {ratio:.6f} ", bg="white", fg="black")
        self.text_show.pack(pady=10)
        # Calculate using formula with closest_above
        if closest_below:
            formula_result = ratio * abs(y5 - closest_below[1])
            print("formula_result : " , abs(y5 - closest_below[1]))

            print(f"Formula Result (Closest Below): {formula_result:.6f} m")
            self.text_show = tk.Label(self.root, text=f"Formula Result : {formula_result:.6f} m", bg="white", fg="black")
            self.text_show.pack(pady=10)
            
        # === คำนวณระยะทางของเส้น cyan ===
        if closest_left:
            dist_left = abs(x5 - closest_left[0])
            print(f"Distance to closest left intersection: {dist_left:.2f} px")
        if closest_right:
            dist_right = abs(x5 - closest_right[0])
            print(f"Distance to closest right intersection: {dist_right:.2f} px")
        if closest_above:
            dist_above = abs(y5 - closest_above[1])
            print(f"Distance to closest above intersection: {dist_above:.2f} px")
        if closest_below:
            dist_below = abs(y5 - closest_below[1])
            print(f"Distance to closest below intersection: {dist_below:.2f} px")

        print(marked)

    def get_intersection(self, x1, y1, x2, y2, x3, y3, x4, y4):
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return None  # ขนานกัน

        px = ((x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4)) / denom
        py = ((x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4)) / denom

        # ตรวจสอบว่า px, py อยู่ในช่วงของทั้งสองเส้น
        if (min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2) and
            min(x3, x4) <= px <= max(x3, x4) and min(y3, y4) <= py <= max(y3, y4)):
            return (px, py)
        return None


    def calculate_distances(self):
        dotfive = self.dots["dot5"]
        x5, y5 = self.get_center(dotfive)
        print(f"Dot5: ({x5:.2f}, {y5:.2f})")
        ball_px = np.float32([[x5, y5]])
        dot1 = self.dots["dot1"]
        dot2 = self.dots["dot2"]
        dot3 = self.dots["dot3"]
        dot4 = self.dots["dot4"]
        x1, y1 = self.get_center(dot1)
        x2, y2 = self.get_center(dot2)
        x3, y3 = self.get_center(dot3)
        x4, y4 = self.get_center(dot4)
        src_pts = np.float32([
            [x1, y1],  # top-left
            [x2, y2],  # bottom-left
            [x3, y3],  # top-right
            [x4, y4],  # bottom-right
        ])
        print(src_pts)
        src_pts = np.float32([
            [320, 385],  # top-left
            [596, 390],  # bottom-left
            [124, 528],  # top-right
            [775, 549],  # bottom-right
        ])
        print(src_pts)
        dst_pts = np.float32([
            [0, 0],       # top-left
            [0, 500],     # bottom-left
            [400, 0],     # top-right
            [400, 500],   # bottom-right
        ])
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        ball_pt = ball_px.reshape(1, 1, 2)  # or: np.array([[[478, 327]]], dtype=np.float32)

        # Step 5: Apply the perspective transformation
        ball_real = cv2.perspectiveTransform(ball_pt, matrix)

        # Step 6: Extract and print the result
        x_cm, y_cm = ball_real[0][0]
        print(f"Ball position in real world: x = {x_cm:.2f} cm, y = {y_cm:.2f} cm")

class TopViewTransformer: #class สำหรับแปลงเป็น TOP Veiw
    def point(self, src_points, dst_size=(600, 800)):
        self.src_points = np.float32(src_points)
        self.dst_points = np.float32([
            [0, 0],  # Top-left
            [dst_size[0], 0],  # Top-right
            [0, dst_size[1]],  # Bottom-left
            [dst_size[0], dst_size[1]]  # Bottom-right
        ])
        self.dst_size = dst_size
        self.matrix = cv2.getPerspectiveTransform(self.src_points, self.dst_points)
        self.inv_matrix = cv2.getPerspectiveTransform(self.dst_points, self.src_points)

    def transform(self, frame):
        return cv2.warpPerspective(frame, self.matrix, self.dst_size)
    
    def transform_point(self, point):
        """Transform a single point using the perspective matrix"""
        if len(point.shape) == 2:
            point = point.reshape(1, 1, 2)
        return cv2.perspectiveTransform(point, self.matrix)
    
    def transform_points(self, points):
        """Transform multiple points using the perspective matrix"""
        if len(points.shape) == 2:
            points = points.reshape(-1, 1, 2)
        return cv2.perspectiveTransform(points, self.matrix)


if __name__ == "__main__":
    image_path = r"/Users/nattavipolboonsangchaitawat/Documents/lab/plc/img_test_copy/20250424_151400.jpg"
    if not os.path.exists(image_path):
        print(f"Please make sure '{image_path}' exists in the specified path.")
    else:
        # Resize image to fit
        max_width, max_height = 600, 800
        with Image.open(image_path) as img:
            img.thumbnail((max_width, max_height))
            resized_image_path = r"/Users/nattavipolboonsangchaitawat/Documents/lab/plc/img_test_copy/20250424_151400.jpg"
            img.save(resized_image_path)
            image_path = resized_image_path
        root = tk.Tk()
        app = ImageWithDotsApp(root, image_path)
        root.mainloop()
        



# root.mainloop()  # Moved inside the `if __name__ == "__main__":` block("WM_DELETE_WINDOW", on_close)