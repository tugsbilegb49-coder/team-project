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
- 👀 Optional head-pose heuristic to reduce false positives (e.g. a phone
  sitting untouched on the desk shouldn't count as "phone time")
- 📝 CSV event log (timestamp, state, duration) — no video is stored
- 📊 Streamlit dashboard for daily/weekly breakdowns and charts
- ⚙️ Fully configurable via `config.yaml`
- ✅ Unit-tested state machine logic (no camera required to test)

## Project structure

```
worker-activity-monitor/
├── config.yaml              # camera index, thresholds, feature flags
├── main.py                  # entry point — starts the monitor
├── requirements.txt
├── src/
│   ├── detector.py          # YOLOv8 wrapper
│   ├── gaze.py              # optional head-pose / attention heuristic
│   ├── activity_tracker.py  # state machine (pure logic, unit-testable)
│   ├── logger.py            # CSV event logging + summary helpers
│   └── monitor.py           # webcam loop that wires everything together
├── dashboard/
│   └── app.py                # Streamlit dashboard reading the CSV log
├── tests/
│   └── test_activity_tracker.py
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
log_file: data/activity_log.csv
```

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

If `use_gaze_heuristic` is enabled, a rough head-pose estimate (via
MediaPipe face landmarks) is used to avoid counting a phone as "in use" if
the person's head is oriented toward the laptop screen rather than down at
their hand.

## Roadmap / ideas for contributions

- [ ] Per-person tracking for multi-desk/open-office setups (e.g. DeepSORT)
- [ ] Proper gaze-vector estimation instead of the coarse heuristic
- [ ] SQLite backend as an alternative to CSV
- [ ] Export to PDF/weekly email report
- [ ] Dockerfile for easy deployment

## License

MIT — see [LICENSE](LICENSE).
