import cv2
from ultralytics import YOLO
import numpy as np

def detect_balls_in_realtime(conf_threshold=0.01):
    model = YOLO('best.pt')  # Load your trained YOLO model

    cap = cv2.VideoCapture(0)  # Use 0 for default webcam, or change to video file path or camera index

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        height, width = frame.shape[:2]
        results = model.predict(frame, save=False)

        all_detections = []
        for result in results:
            for box, conf, cls_id in zip(
                result.boxes.xyxy.cpu().numpy(),
                result.boxes.conf.cpu().numpy(),
                result.boxes.cls.cpu().numpy().astype(int)
            ):
                x1, y1, x2, y2 = map(int, box)
                all_detections.append({
                    'bbox': (x1, y1, x2, y2),
                    'confidence': conf,
                    'class': cls_id
                })

        boxes = [[x1, y1, x2 - x1, y2 - y1] for x1, y1, x2, y2 in (det['bbox'] for det in all_detections)]
        confidences = [det['confidence'] for det in all_detections]

        nms_indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, 0.1) if len(boxes) > 0 else []
        if len(nms_indices) > 0:
            if isinstance(nms_indices, np.ndarray):
                nms_indices = nms_indices.flatten().tolist()
            elif isinstance(nms_indices[0], (list, tuple)):
                nms_indices = [i[0] for i in nms_indices]

            filtered_detections = [all_detections[i] for i in nms_indices]
        else:
            filtered_detections = []

        for i, det in enumerate(filtered_detections):
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            class_name = ""
            if det['class'] == 0:
                class_name = "Blue"
            elif det['class'] == 1:
                class_name = "White"
            elif det['class'] == 2:
                class_name = "Red"

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{class_name} {i+1}: {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Real-Time Ball Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Run the function
detect_balls_in_realtime()
