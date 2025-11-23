from ultralytics import YOLO

# Load a YOLOv8 model (you can also use 'yolov8n', 'yolov8s', etc.)
model = YOLO('yolov8n.pt')  # pretrained weights

# Train the model using your data.yaml
model.train(
    data='data.yaml',
    epochs=10,
    imgsz=640,
    batch=16
)
