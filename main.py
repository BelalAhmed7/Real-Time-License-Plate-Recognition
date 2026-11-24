"""Real-time license plate recognition pipeline.

Detects vehicles with a YOLOv8 model pre-trained on COCO, tracks them
across frames, localizes license plates with a fine-tuned YOLOv8
detector and reads the plate text with EasyOCR. Results are written to
test.csv for visualize.py.
"""

import argparse

import cv2
import numpy as np
from ultralytics import YOLO

from tracker import IouTracker
from util import get_car, read_license_plate, write_csv

# COCO class ids for motor vehicles.
VEHICLES = [2, 3, 5, 7]


def main():
    parser = argparse.ArgumentParser(description='License plate recognition on a video.')
    parser.add_argument('--video', default='./sample.mp4', help='Path to the input video.')
    parser.add_argument('--output', default='./test.csv', help='Path to the output CSV.')
    parser.add_argument('--vehicle-model', default='yolov8n.pt', help='YOLOv8 weights for vehicle detection.')
    parser.add_argument('--plate-model', default='license_plate_detector.pt', help='Fine-tuned YOLOv8 weights for plate detection.')
    args = parser.parse_args()

    results = {}

    tracker = IouTracker()

    # Load models.
    coco_model = YOLO(args.vehicle_model)
    license_plate_detector = YOLO(args.plate_model)

    # Load video.
    cap = cv2.VideoCapture(args.video)

    frame_nmr = -1
    ret = True
    while ret:
        frame_nmr += 1
        ret, frame = cap.read()
        if ret:
            results[frame_nmr] = {}

            # Detect vehicles.
            detections = coco_model(frame)[0]
            detections_ = []
            for detection in detections.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = detection
                if int(class_id) in VEHICLES:
                    detections_.append([x1, y1, x2, y2, score, class_id])

            # Track vehicles.
            track_ids = tracker.update(detections_)

            # Detect license plates.
            license_plates = license_plate_detector(frame)[0]
            for license_plate in license_plates.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = license_plate

                # Assign the plate to a tracked car.
                xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)

                if car_id != -1:
                    # Crop and read the license plate.
                    license_plate_crop = frame[int(y1):int(y2), int(x1):int(x2), :]

                    # Preprocess the crop for OCR.
                    license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
                    _, license_plate_crop_thresh = cv2.threshold(
                        license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)

                    # Read the license plate number.
                    license_plate_text, license_plate_text_score = read_license_plate(license_plate_crop_thresh)

                    if license_plate_text is not None:
                        results[frame_nmr][car_id] = {
                            'car': {'bbox': [xcar1, ycar1, xcar2, ycar2]},
                            'license_plate': {
                                'bbox': [x1, y1, x2, y2],
                                'text': license_plate_text,
                                'bbox_score': score,
                                'text_score': license_plate_text_score,
                            },
                        }

    # Write results.
    write_csv(results, args.output)
    cap.release()
    print('Wrote results to {}'.format(args.output))


if __name__ == '__main__':
    main()
