"""Lightweight IoU-based multi-object tracker.

Assigns a persistent ID to every detection by greedily matching new
bounding boxes against active tracks with intersection-over-union.
"""


class Track:
    _next_id = 0

    def __init__(self, bbox):
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.id = Track._next_id
        Track._next_id += 1
        self.missed = 0


def iou(box_a, box_b):
    """Intersection-over-union of two [x1, y1, x2, y2] boxes."""
    x_left = max(box_a[0], box_b[0])
    y_top = max(box_a[1], box_b[1])
    x_right = min(box_a[2], box_b[2])
    y_bottom = min(box_a[3], box_b[3])

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection = (x_right - x_left) * (y_bottom - y_top)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - intersection

    return intersection / union if union > 0 else 0.0


class IouTracker:
    """Greedy IoU tracker with a simple max-age eviction policy."""

    def __init__(self, iou_threshold=0.3, max_age=10):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.tracks = []

    def update(self, detections):
        """Match detections to tracks.

        Args:
            detections: iterable of [x1, y1, x2, y2, score, class_id].

        Returns:
            List of [x1, y1, x2, y2, track_id] for every matched or new track.
        """
        output = []
        used_tracks = set()

        for det in detections:
            bbox = det[:4]
            best_track, best_iou = None, self.iou_threshold

            for track in self.tracks:
                if track.id in used_tracks:
                    continue
                score = iou(bbox, track.bbox)
                if score > best_iou:
                    best_iou = score
                    best_track = track

            if best_track is None:
                best_track = Track(bbox)
                self.tracks.append(best_track)
            else:
                best_track.bbox = bbox
                best_track.missed = 0

            used_tracks.add(best_track.id)
            output.append([bbox[0], bbox[1], bbox[2], bbox[3], best_track.id])

        # Age out tracks that were not matched this frame.
        for track in self.tracks:
            if track.id not in used_tracks:
                track.missed += 1
        self.tracks = [t for t in self.tracks if t.missed <= self.max_age]

        return output
