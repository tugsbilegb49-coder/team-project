# Worker Activity Monitor

A computer-vision tool that watches a webcam feed and estimates how much time
a person spends **working at their laptop**, **using their phone**, **idle**,
or **away from their desk** — using real-time object detection (YOLOv8).

It logs every state change to disk and ships with a small dashboard for
reviewing daily/weekly summaries.

> ⚠️ **Use responsibly.** This is workplace monitoring software. In most
> jurisdictions you are legally required to disclose this kind of monitoring
> to the people being recorded, and some jurisdictions restrict or ban it
> entirely. Get informed consent, be transparent about what's logged (this
> tool stores only timestamps + state labels, never video, by default), and
> check local labor law before deploying it.

---

## Features

- 🎯 Real-time detection of `person`, `laptop`, and `cell phone` via YOLOv8
- 🧠 Simple state machine: `WORKING`, `PHONE`, `IDLE`, `AWAY`
- 👀 Real head-pose estimation (6-point 3D model + `cv2.solvePnP`, recovering
  actual yaw/pitch/roll angles) to reduce false positives — a phone sitting
  untouched on the desk shouldn't count as "phone time"
- 👥 **Multi-person mode**: tracks each visible person with a stable ID via
  DeepSORT and maintains a separate activity state per person, for
  open-office/multi-desk camera feeds
- 📝 CSV event log (timestamp, state, duration, optional person_id) — no
  video is stored
- 📊 Streamlit dashboard for daily/weekly breakdowns, with a per-person view
  when multi-person mode is on
- ⚙️ Fully configurable via `config.yaml`
- ✅ 17 unit tests covering the state machine, object-to-person association
  geometry, and the head-pose math — none require a camera or GPU

## Project structure

```
worker-activity-monitor/
├── config.yaml              # camera index, thresholds, feature flags
├── main.py                  # entry point — starts the monitor
├── requirements.txt
├── src/
│   ├── detector.py          # YOLOv8 wrapper
│   ├── gaze.py              # solvePnP-based head-pose (yaw/pitch/roll) estimation
│   ├── person_tracker.py    # DeepSORT wrapper — stable per-person track IDs
│   ├── association.py       # geometry: assign laptop/phone boxes to the nearest person
│   ├── activity_tracker.py  # state machine (pure logic, unit-testable)
│   ├── logger.py            # CSV event logging + summary helpers
│   ├── monitor.py           # single-person webcam loop
│   └── multi_monitor.py     # multi-person webcam loop (DeepSORT + per-person state)
├── dashboard/
│   └── app.py                # Streamlit dashboard reading the CSV log
├── tests/
│   ├── test_activity_tracker.py
│   ├── test_association.py
│   └── test_gaze.py
└── data/
    └── activity_log.csv      # generated at runtime (gitignored)
```

## Setup

```bash
git clone https://github.com/<your-username>/worker-activity-monitor.git
cd worker-activity-monitor
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Start monitoring:

```bash
python main.py
```

- Press `q` in the video window to stop.
- A session summary prints to the console; the full event log is appended to
  `data/activity_log.csv`.

View the dashboard:

```bash
streamlit run dashboard/app.py
```

## Configuration

Edit `config.yaml`:

```yaml
camera_index: 0
model_name: yolov8n.pt
confidence_threshold: 0.45
detect_every_n_frames: 5
use_gaze_heuristic: false
multi_person: false      # set true for open-office / multi-desk camera feeds
track_max_age: 30        # DeepSORT: frames a lost track survives before dropping
log_file: data/activity_log.csv
```

Setting `multi_person: true` switches `main.py` to `MultiPersonMonitor`,
which tracks every visible person with DeepSORT, assigns the nearest
laptop/phone detections to each one, and logs a separate activity timeline
per `person_id` in the same CSV file. The dashboard automatically detects
this and adds a per-person filter and breakdown chart.

## Running tests

```bash
pytest tests/
```

## How the classification works

Each processed frame is run through YOLOv8, which returns bounding boxes for
any of COCO's 80 object classes. We only care about three:

| Detected                          | State     |
|------------------------------------|-----------|
| `cell phone` present                | `PHONE`   |
| `person` + `laptop`, no phone       | `WORKING` |
| `person` only                       | `IDLE`    |
| nothing relevant                    | `AWAY`    |

If `use_gaze_heuristic` is enabled, a real head-pose estimate (MediaPipe
Face Mesh landmarks + `cv2.solvePnP`, giving actual yaw/pitch/roll in
degrees — see `src/gaze.py`) is used to avoid counting a phone as "in use"
if the person's head is oriented toward the laptop screen rather than down
at their hand.

### Multi-person mode, in more detail

1. YOLOv8 detects all `person`, `laptop`, and `cell phone` boxes in the frame.
2. `person_tracker.py` (DeepSORT) assigns a stable ID to each person box, so
   the same individual keeps the same ID across frames even through brief
   occlusion.
3. `association.py` assigns each laptop/phone box to the *nearest* tracked
   person (by bounding-box center distance, capped relative to that
   person's box size, so a phone across the room isn't misattributed).
4. Each person ID gets its own `ActivityTracker` state machine and its own
   row in the CSV log (`person_id` column).

## Roadmap / ideas for contributions

- [ ] SQLite backend as an alternative to CSV
- [ ] Export to PDF/weekly email report
- [ ] Dockerfile for easy deployment
- [ ] Re-identification across camera restarts (currently DeepSORT IDs reset
      each run)

## License

MIT — see [LICENSE](LICENSE).
