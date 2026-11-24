"""Fill gaps in the detection CSV by interpolating bounding boxes.

For every tracked car, frames where the detector missed the car or its
plate are reconstructed by linear interpolation between the surrounding
detections, giving a smooth track for visualization.
"""

import argparse
import csv

import numpy as np


def interpolate_bounding_boxes(data):
    """Interpolate missing car and plate bounding boxes per car id."""
    # Extract necessary columns.
    frame_numbers = np.array([int(row['frame_nmr']) for row in data])
    car_ids = np.array([int(float(row['car_id'])) for row in data])
    car_bboxes = np.array([list(map(float, row['car_bbox'][1:-1].split())) for row in data])
    license_plate_bboxes = np.array([list(map(float, row['license_plate_bbox'][1:-1].split())) for row in data])

    interpolated_data = []
    unique_car_ids = np.unique(car_ids)

    for car_id in unique_car_ids:
        frame_numbers_ = frame_numbers[car_ids == car_id]

        # Interpolate across the full span of frames where the car appears.
        first_frame, last_frame = frame_numbers_[0], frame_numbers_[-1]
        for i in range(len(frame_numbers_)):
            frame_nmr = frame_numbers_[i]
            row_mask = (frame_numbers == frame_nmr) & (car_ids == car_id)
            row_index = np.where(row_mask)[0][0]

            if i > 0 and frame_nmr - frame_numbers_[i - 1] > 1:
                # There is a gap: interpolate between the previous and current detection.
                prev_frame = frame_numbers_[i - 1]
                gap = frame_nmr - prev_frame
                prev_car = car_bboxes[car_ids == car_id][i - 1]
                curr_car = car_bboxes[car_ids == car_id][i]
                prev_plate = license_plate_bboxes[car_ids == car_id][i - 1]
                curr_plate = license_plate_bboxes[car_ids == car_id][i]

                for step in range(1, gap):
                    alpha = step / gap
                    new_frame = prev_frame + step
                    interp_car = (1 - alpha) * prev_car + alpha * curr_car
                    interp_plate = (1 - alpha) * prev_plate + alpha * curr_plate
                    interpolated_data.append({
                        'frame_nmr': str(new_frame),
                        'car_id': str(car_id),
                        'car_bbox': '[{} {} {} {}]'.format(*interp_car),
                        'license_plate_bbox': '[{} {} {} {}]'.format(*interp_plate),
                        'license_plate_bbox_score': '0',
                        'license_number': '0',
                        'license_number_score': '0',
                    })

            interpolated_data.append({
                'frame_nmr': str(data[row_index]['frame_nmr']),
                'car_id': str(data[row_index]['car_id']),
                'car_bbox': data[row_index]['car_bbox'],
                'license_plate_bbox': data[row_index]['license_plate_bbox'],
                'license_plate_bbox_score': data[row_index]['license_plate_bbox_score'],
                'license_number': data[row_index]['license_number'],
                'license_number_score': data[row_index]['license_number_score'],
            })

    return interpolated_data


def main():
    parser = argparse.ArgumentParser(description='Interpolate missing detections in the results CSV.')
    parser.add_argument('--input', default='./test.csv', help='CSV produced by main.py.')
    parser.add_argument('--output', default='./test_interpolated.csv', help='Interpolated CSV.')
    args = parser.parse_args()

    # Load the CSV.
    with open(args.input, 'r', newline='') as file:
        reader = csv.DictReader(file)
        data = list(reader)

    # Interpolate.
    interpolated_data = interpolate_bounding_boxes(data)

    # Write the updated CSV.
    header = ['frame_nmr', 'car_id', 'car_bbox', 'license_plate_bbox',
              'license_plate_bbox_score', 'license_number', 'license_number_score']
    with open(args.output, 'w') as file:
        file.write(','.join(header) + '\n')
        for row in interpolated_data:
            file.write(','.join(row[col] for col in header) + '\n')

    print('Wrote interpolated results to {}'.format(args.output))


if __name__ == '__main__':
    main()
