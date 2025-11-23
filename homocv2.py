import cv2
import numpy as np
from PIL import Image

# # กำหนดจุดที่รู้จักในภาพต้นทาง (เช่นมุม 4 มุมของวัตถุที่ต้องการแปลง)
src_points = np.float32([[100, 150], [400, 150], [100, 400], [400, 400]])

# # กำหนดจุดที่ต้องการให้เป็นมุมมองจากมุมบน (ตามขนาดของภาพปลายทาง)
dst_points = np.float32([[0, 0], [500, 0], [0, 500], [500, 500]])

# # คำนวณ Homography matrix
H, status = cv2.findHomography(src_points, dst_points)

# โหลดภาพต้นทาง
img_src = cv2.imread("/Users/nattavipolboonsangchaitawat/Documents/lab/plc/img/IMG_7220.jpg")  # Replace with your source image path

# ขนาดของภาพต้นทาง
height, width, channels = img_src.shape
# Resize image to fit

max_width, max_height = 800, 600
resized_image_path = "/Users/nattavipolboonsangchaitawat/Documents/lab/plc/img/resized_image.jpg"
with Image.open("/Users/nattavipolboonsangchaitawat/Documents/lab/plc/img/IMG_7220.jpg") as img:
    img.thumbnail((max_width, max_height))
    img.save(resized_image_path)

# Reload the resized image
img_src = cv2.imread(resized_image_path)
height, width, channels = img_src.shape

# ใช้ Homography matrix เพื่อแปลงภาพต้นทางให้เป็นมุมมองจากมุมบน
img_topdown = cv2.warpPerspective(img_src, H, (500, 500))  # ขนาดภาพปลายทาง

# แสดงภาพที่แปลงแล้ว
cv2.imshow("Top-Down View", img_src)
cv2.waitKey(0)
cv2.destroyAllWindows()
