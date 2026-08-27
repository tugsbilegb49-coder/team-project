"""
gaze.py
-------
Optional, lightweight heuristic to reduce false "PHONE" positives: instead
of counting any visible phone as "in use", estimate whether the person's
head is tilted downward (as when looking at a phone in hand) versus level
or up (as when looking at a laptop screen).

This is intentionally simple — a coarse heuristic based on the vertical
position of facial landmarks, not true 3D gaze estimation. It's good enough
to filter out "phone lying untouched on the desk" cases, but treat it as an
approximation, not ground truth.

Requires: mediapipe
"""

from typing import Optional
import numpy as np

try:
    import mediapipe as mp
    _HAS_MEDIAPIPE = True
except ImportError:
    _HAS_MEDIAPIPE = False


class GazeHeuristic:
    def __init__(self, downward_pitch_threshold: float = 12.0):
        """
        downward_pitch_threshold: degrees of downward head tilt (relative to
        a level baseline) beyond which we consider the person to be looking
        down at something in their hands rather than at a screen in front
        of them.
        """
        if not _HAS_MEDIAPIPE:
            raise ImportError(
                "mediapipe is required for the gaze heuristic. "
                "Install it with `pip install mediapipe`."
            )
        self.threshold = downward_pitch_threshold
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
        )

    def is_looking_down(self, frame: np.ndarray) -> Optional[bool]:
        """Returns True if the head appears tilted down, False if level/up,
        or None if no face could be found in the frame."""
        h, w = frame.shape[:2]
        results = self.face_mesh.process(frame[:, :, ::-1])  # BGR -> RGB
        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0].landmark

        # Rough pitch proxy: vertical offset between the forehead point and
        # the chin point, normalized by face height. A larger-than-baseline
        # offset (chin pulled up / forehead pulled down) suggests a downward
        # tilt. This is a coarse approximation, not a calibrated 3D pose.
        forehead = landmarks[10]
        chin = landmarks[152]
        nose_tip = landmarks[1]

        face_height = abs(chin.y - forehead.y) * h
        if face_height == 0:
            return None

        # Nose position relative to the forehead-chin midline shifts down
        # when the head tilts forward/down.
        midline_y = (forehead.y + chin.y) / 2
        offset = (nose_tip.y - midline_y) * h
        pitch_estimate_deg = (offset / face_height) * 90  # rough scaling

        return pitch_estimate_deg > self.threshold

    def close(self):
        self.face_mesh.close()
