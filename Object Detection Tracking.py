"""
CodeAlpha Internship — Task 4: Object Detection and Tracking
=============================================================
Requirements covered:
  ✅ Real-time video input via webcam OR video file (OpenCV)
  ✅ YOLOv8 pre-trained model for object detection
  ✅ Bounding boxes drawn on each frame with class labels
  ✅ Object tracking using SORT algorithm (Simple Online and Realtime Tracking)
  ✅ Output displayed with labels and tracking IDs in real time

Dependencies:
  pip install ultralytics opencv-python numpy scipy filterpy
"""

import cv2
import numpy as np
import argparse
import time
import random
from ultralytics import YOLO


# ─────────────────────────────────────────────
#  SORT Tracker (lightweight implementation)
#  Based on: https://github.com/abewley/sort
# ─────────────────────────────────────────────
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment


def iou(bb_test, bb_gt):
    """Compute IoU between two bounding boxes [x1,y1,x2,y2]."""
    xx1 = max(bb_test[0], bb_gt[0])
    yy1 = max(bb_test[1], bb_gt[1])
    xx2 = min(bb_test[2], bb_gt[2])
    yy2 = min(bb_test[3], bb_gt[3])
    w = max(0.0, xx2 - xx1)
    h = max(0.0, yy2 - yy1)
    intersection = w * h
    area_test = (bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1])
    area_gt   = (bb_gt[2]   - bb_gt[0])   * (bb_gt[3]   - bb_gt[1])
    union = area_test + area_gt - intersection
    return intersection / union if union > 0 else 0.0


class KalmanBoxTracker:
    """Represents a tracked object using a Kalman Filter."""
    count = 0

    def __init__(self, bbox):
        # State: [x, y, s, r, dx, dy, ds]  (center_x, center_y, scale, ratio, velocities)
        self.kf = KalmanFilter(dim_x=7, dim_z=4)
        self.kf.F = np.array([
            [1,0,0,0,1,0,0],
            [0,1,0,0,0,1,0],
            [0,0,1,0,0,0,1],
            [0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0],
            [0,0,0,0,0,1,0],
            [0,0,0,0,0,0,1],
        ], dtype=np.float64)
        self.kf.H = np.array([
            [1,0,0,0,0,0,0],
            [0,1,0,0,0,0,0],
            [0,0,1,0,0,0,0],
            [0,0,0,1,0,0,0],
        ], dtype=np.float64)
        self.kf.R[2:, 2:] *= 10.0
        self.kf.P[4:, 4:] *= 1000.0
        self.kf.P *= 10.0
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01
        self.kf.x[:4] = self._xyxy_to_z(bbox)

        KalmanBoxTracker.count += 1
        self.id = KalmanBoxTracker.count
        self.hits = 0
        self.no_loss = 0
        self.age = 0
        self.label = ""

    @staticmethod
    def _xyxy_to_z(bbox):
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        cx = bbox[0] + w / 2.0
        cy = bbox[1] + h / 2.0
        s = w * h
        r = w / float(h) if h > 0 else 1
        return np.array([[cx], [cy], [s], [r]], dtype=np.float64)

    def _x_to_xyxy(self):
        s, r = self.kf.x[2, 0], self.kf.x[3, 0]
        w = np.sqrt(abs(s * r))
        h = s / w if w > 0 else 0
        cx, cy = self.kf.x[0, 0], self.kf.x[1, 0]
        return [cx - w/2, cy - h/2, cx + w/2, cy + h/2]

    def predict(self):
        if self.kf.x[6, 0] + self.kf.x[2, 0] <= 0:
            self.kf.x[6] = 0
        self.kf.predict()
        self.age += 1
        self.no_loss += 1
        return self._x_to_xyxy()

    def update(self, bbox):
        self.no_loss = 0
        self.hits += 1
        self.kf.update(self._xyxy_to_z(bbox))

    def get_state(self):
        return self._x_to_xyxy()


class SORTTracker:
    """SORT: Simple Online and Realtime Tracking."""

    def __init__(self, max_age=30, min_hits=2, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers: list[KalmanBoxTracker] = []
        self.frame_count = 0

    def update(self, detections: np.ndarray, labels: list[str]) -> list:
        """
        detections: Nx5 array [x1,y1,x2,y2,score]
        labels:     list of N label strings
        Returns list of [x1,y1,x2,y2,track_id,label]
        """
        self.frame_count += 1

        # Predict existing trackers
        predicted = []
        remove = []
        for t in self.trackers:
            box = t.predict()
            if any(np.isnan(box)):
                remove.append(t)
            else:
                predicted.append(box)
        for t in remove:
            self.trackers.remove(t)

        # Match detections to trackers via IoU
        if len(predicted) > 0 and len(detections) > 0:
            iou_matrix = np.zeros((len(detections), len(predicted)), dtype=np.float64)
            for d, det in enumerate(detections):
                for t, pred in enumerate(predicted):
                    iou_matrix[d, t] = iou(det[:4], pred)

            row_ind, col_ind = linear_sum_assignment(-iou_matrix)
            matched_d = set()
            matched_t = set()
            for r, c in zip(row_ind, col_ind):
                if iou_matrix[r, c] >= self.iou_threshold:
                    self.trackers[c].update(detections[r, :4])
                    self.trackers[c].label = labels[r] if r < len(labels) else ""
                    matched_d.add(r)
                    matched_t.add(c)

            # New trackers for unmatched detections
            for d in range(len(detections)):
                if d not in matched_d:
                    t = KalmanBoxTracker(detections[d, :4])
                    t.label = labels[d] if d < len(labels) else ""
                    self.trackers.append(t)
        else:
            for d, det in enumerate(detections):
                t = KalmanBoxTracker(det[:4])
                t.label = labels[d] if d < len(labels) else ""
                self.trackers.append(t)

        # Remove dead trackers
        results = []
        live = []
        for t in self.trackers:
            if t.no_loss <= self.max_age:
                live.append(t)
                if t.hits >= self.min_hits or self.frame_count <= self.min_hits:
                    box = t.get_state()
                    results.append([*box, t.id, t.label])
        self.trackers = live
        return results


# ─────────────────────────────────────────────
#  Color palette per track ID
# ─────────────────────────────────────────────
_id_colors: dict[int, tuple] = {}
def get_color(track_id: int) -> tuple:
    if track_id not in _id_colors:
        random.seed(track_id * 7 + 13)
        _id_colors[track_id] = (
            random.randint(80, 255),
            random.randint(80, 255),
            random.randint(80, 255),
        )
    return _id_colors[track_id]


# ─────────────────────────────────────────────
#  Draw helpers
# ─────────────────────────────────────────────
def draw_box(frame, x1, y1, x2, y2, track_id, label, conf):
    color = get_color(track_id)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # Label background
    caption = f"ID:{track_id} {label} {conf:.0%}" if conf else f"ID:{track_id} {label}"
    (tw, th), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
    cv2.putText(frame, caption, (x1 + 3, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)


def draw_overlay(frame, fps, n_objects, source_label):
    h, w = frame.shape[:2]
    # Semi-transparent top bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 36), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    cv2.putText(frame, f"CodeAlpha | Object Detection & Tracking",
                (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, f"FPS: {fps:.1f}  Objects: {n_objects}  Source: {source_label}",
                (w - 330, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 160), 1, cv2.LINE_AA)


# ─────────────────────────────────────────────
#  Main Detection + Tracking Loop
# ─────────────────────────────────────────────
def run(source, model_name="yolov8n.pt", conf_thresh=0.4, target_classes=None):
    """
    source       : 0 for webcam, or path to video file
    model_name   : YOLOv8 model variant (yolov8n.pt is smallest/fastest)
    conf_thresh  : Minimum detection confidence
    target_classes: List of class names to detect (None = all)
    """
    print(f"[INFO] Loading YOLO model: {model_name}")
    model = YOLO(model_name)
    tracker = SORTTracker(max_age=30, min_hits=2, iou_threshold=0.3)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source}")
        return

    source_label = "Webcam" if source == 0 else source.split("/")[-1]
    print(f"[INFO] Running on: {source_label}. Press Q to quit.")

    prev_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] Stream ended.")
            break

        # ── YOLO Detection ──
        results = model(frame, verbose=False)[0]
        detections = []
        det_labels  = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            label  = model.names[cls_id]

            if conf < conf_thresh:
                continue
            if target_classes and label not in target_classes:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            detections.append([x1, y1, x2, y2, conf])
            det_labels.append(label)

        # ── SORT Tracking ──
        det_array = np.array(detections, dtype=np.float64) if detections else np.empty((0, 5))
        tracked = tracker.update(det_array, det_labels)

        # ── Draw bounding boxes ──
        conf_map = {}  # track_id -> conf (approximate)
        for i, (det, lbl) in enumerate(zip(detections, det_labels)):
            pass  # conf values already embedded in det_array

        for obj in tracked:
            x1, y1, x2, y2, track_id, label = obj
            draw_box(frame, int(x1), int(y1), int(x2), int(y2),
                     int(track_id), label, 0.0)

        # ── FPS & Overlay ──
        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time + 1e-6)
        prev_time = curr_time
        draw_overlay(frame, fps, len(tracked), source_label)

        cv2.imshow("CodeAlpha — Object Detection & Tracking (Q to quit)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Done.")


# ─────────────────────────────────────────────
#  CLI Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CodeAlpha Task 4 — Object Detection & Tracking")
    parser.add_argument(
        "--source", default="0",
        help="Video source: 0 for webcam, or path to a video file"
    )
    parser.add_argument(
        "--model", default="yolov8n.pt",
        help="YOLO model variant: yolov8n.pt | yolov8s.pt | yolov8m.pt"
    )
    parser.add_argument(
        "--conf", type=float, default=0.4,
        help="Detection confidence threshold (0.0 – 1.0)"
    )
    parser.add_argument(
        "--classes", nargs="+", default=None,
        help="Filter to specific classes, e.g. --classes person car"
    )
    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source
    run(source=source, model_name=args.model,
        conf_thresh=args.conf, target_classes=args.classes)