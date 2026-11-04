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
- 📊 Streamlit dashboard for local logs or authenticated Django API data
- 🔐 Consent records, device enrollment, local pause/resume, and offline queues
- ⚙️ Fully configurable via `config.yaml`
- ✅ 17 unit tests covering the state machine, object-to-person association
  geometry, and the head-pose math — none require a camera or GPU

## Project structure

```
worker-activity-monitor/
├── config.yaml              # camera index, thresholds, feature flags
├── main.py                  # entry point — starts the monitor
├── requirements.txt
├── agent/                   # desktop agent and macOS/Windows autostart installers
├── backend/                 # Django API, roles, consent, devices, scores and Dockerfile
├── docker-compose.yml        # PostgreSQL + Django + daily score scheduler
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
│   └── app.py                # Streamlit dashboard for local CSV or Django API data
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

- [x] Django REST API with JWT authentication, roles, consent, devices, and daily score calculation
- [x] Docker/PostgreSQL deployment configuration and daily score scheduler
- [x] macOS LaunchAgent and Windows Task Scheduler installer scripts
- [ ] Export to PDF/weekly email report
- [ ] Dockerfile for easy deployment
- [ ] Re-identification across camera restarts (currently DeepSORT IDs reset
      each run)

## Django backend API

The webcam application and API run as separate services. The webcam monitor
continues to write CSV events and, after the desktop agent is logged in, sends
completed camera events directly to Django. Django manages users and tasks,
then calculates productivity scores.

```text
camera -> data/activity_log.csv -> Django import -> database -> API
macOS/Windows agent -> /api/computer-activity/ingest/ -> database -> API
```

### Start the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`. Use the Django admin at
`/admin/` to create departments and users. A superuser has full API access;
other users should be assigned one of these roles:

- `ADMIN`: manages users, departments, tasks, imported activity and scores.
- `MANAGER`: sees and manages tasks for employees in their own department.
- `EMPLOYEE`: sees only their own profile, tasks, activity events and scores.

### Authentication endpoints

| Method | URL | Purpose |
|---|---|---|
| `POST` | `/api/auth/login/` | Obtain JWT access and refresh tokens. |
| `POST` | `/api/auth/refresh/` | Refresh an access token. |
| `GET` | `/api/users/me/` | Return the current user. |

Send the access token on protected API calls:

```text
Authorization: Bearer <access-token>
```

### Main API resources

- `/api/users/` - user management (write access: admin only)
- `/api/consents/` - employee consent status, grant and revoke actions
- `/api/devices/` - user-approved workstations and device enrollment
- `/api/departments/` - department management (write access: admin only)
- `/api/tasks/` - employee tasks (write access: admin or manager)
- `/api/activity-events/` - imported activity data (write access: admin only)
- `/api/computer-activity/` - foreground application time segments
- `/api/scores/` - read daily scores
- `POST /api/scores/calculate/` - calculate a daily score
- `GET /api/scores/dashboard/?date=YYYY-MM-DD` - dashboard-ready daily aggregates

Example score calculation for employee ID `2` on a day:

```json
POST /api/scores/calculate/
{
  "employee_id": 2,
  "date": "2026-11-05"
}
```

The score formula is `P = 0.4T + 0.3Q + 0.2D + 0.1W`, where all values are
normalized to 0-100:

- `T`: completed tasks / tasks due that day
- `Q`: average manager quality score for completed tasks
- `D`: tasks completed on time / tasks due that day
- `W`: time classified as `WORK` / all desktop-agent time. If the agent has
  not sent data for the day, the camera's `WORKING` time ratio is used.

Scores are classified as `LOW` (0-64), `MEDIUM` (65-84), and `HIGH` (85-100).

### Import webcam events

Create the employee first, then import the existing log. The CSV has no
employee identity in single-person mode, so the command requires a username.

```bash
cd backend
source .venv/bin/activate
python manage.py import_activity_log ../data/activity_log.csv --employee employee_username
```

Importing the same file again is safe: identical event rows are skipped.

For a single-user Mac, new camera sessions normally do not need this manual
import: `config.yaml` enables direct API sync. The camera monitor reuses the
desktop-agent login described below. If Django is unavailable, it still saves
the local CSV and reports that the API sync was skipped.

### Backend tests

```bash
cd backend
source .venv/bin/activate
python manage.py test
```

### Daily score refresh

Run this from the backend server to update scores for all active users:

```bash
python manage.py calculate_daily_scores --date 2026-11-05
```

## Desktop agent (macOS and Windows)

`agent/main.py` is a small, visible terminal process that records the name of
the frontmost macOS or Windows application and the time it stayed active. It
sends each 30-second segment to the authenticated employee's Django account.

It **does not** record keystrokes, screen contents, window titles, document
names, browser URLs, browsing history, screenshots, audio, or video. It should
only be run with the user's informed consent.

### Set up and start the agent

Keep `python manage.py runserver` running in `backend/`, then open a second
terminal at the project root:

```bash
cp agent/config.example.json agent/config.json
```

On Windows PowerShell, use:

```powershell
Copy-Item agent\config.example.json agent\config.json
```

Edit `agent/config.json` and replace `employee_username` with the username you
created in Django admin. You can also add or remove app names from
`productive_apps`; only those names are categorised as `WORK`. Browsers are
kept as `BROWSER` rather than being assumed productive.

Log in once; the password is prompted for and is not put into `config.json`:

```bash
python3 agent/main.py --login
python3 agent/main.py
```

On Windows PowerShell, the equivalent commands are:

```powershell
py agent\main.py --login
py agent\main.py
```

The first login also enrolls the current computer as a device for that user;
the generated device ID is saved in `agent/config.json`. Camera and desktop
events from that computer can then be correlated without relying on a
temporary multi-person tracker ID.

The agent keeps unsent events in a local queue while the API is unavailable,
then uploads them when the connection returns. Local controls are available:

```bash
python3 agent/main.py --status
python3 agent/main.py --pause
python3 agent/main.py --resume
python3 agent/main.py --grant-consent 2026-11
python3 agent/main.py --revoke-consent
```

`--revoke-consent` pauses local monitoring as well. In Docker/production,
`REQUIRE_MONITORING_CONSENT=true` rejects uploads until consent is granted.
The configured `idle_threshold_seconds` (five minutes by default) turns an
inactive keyboard/mouse period into an `Idle` segment. It reads only elapsed
idle time, never keys, clicks, or their content.

Open one more terminal for the camera monitor. The MacBook/laptop built-in
camera is normally `camera_index: 0` in `config.yaml`; a USB camera is often
`1`.

```bash
source .venv/bin/activate
python3 main.py
```

The camera monitor uses the saved agent login to call
`POST /api/activity-events/ingest/` whenever its state changes or stops. It
therefore needs no employee name in the camera configuration and does not ask
the employee to enter activity manually. Multi-person camera mode stays local
CSV-only because a temporary DeepSORT track ID is not a verified employee
identity.

### Start at sign-in

These installer scripts are explicit user actions; inspect them and run them
only after consent, login, and camera permission are configured. They create
user-level entries only, never system-wide services.

macOS:

```bash
python3 agent/install_macos_launch_agent.py
# Remove later with: python3 agent/install_macos_launch_agent.py --uninstall
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\agent\install_windows_startup.ps1
# Remove later with: .\agent\install_windows_startup.ps1 -Uninstall
```

Both installers start the local Django API, desktop agent, and camera monitor
at the next user sign-in. The camera indicator remains controlled by the
operating system. On a shared server deployment, do not install the local API
task; point the agent at the HTTPS server instead.

The saved token is local to the machine, readable only by the current account,
and is excluded from Git. Press `Ctrl+C` to stop.

On macOS, the first run may ask you to permit Terminal or VS Code to automate
`System Events`; grant it only if you are intentionally enabling this agent.
The setting is under **System Settings -> Privacy & Security -> Automation**.
On Windows, the agent uses the foreground process executable name rather than
the window title, so document and file names are not collected. Permit camera
access for the terminal/Python process if you run the camera monitor there.

For a quick code-only check of the agent helpers:

```bash
python3 -m unittest discover -s agent -p "test_*.py"
```

## Dashboard

Start the dashboard with `streamlit run dashboard/app.py`. Choose **Django
API** in the sidebar, log in with an API user, and it will show the selected
day's score, consent state, camera states, and application-time breakdowns.
**Local CSV** remains available for offline inspection.

## PostgreSQL and deployment

For a shared server, copy the environment template and set real secrets:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env: change the secret key, PostgreSQL password, allowed hosts and HTTPS origins.
docker compose --env-file backend/.env up --build -d
```

This starts PostgreSQL, Django/Gunicorn, and a daily score scheduler. Put the
service behind an HTTPS reverse proxy (for example Nginx or Caddy), set the
public hostname in `DJANGO_ALLOWED_HOSTS`, and change each agent's `api_url`
from `http://127.0.0.1:8000` to that HTTPS address. A public deployment still
requires your own server, domain/DNS, and TLS certificate; the project does
not publish itself to the internet.

## License

MIT — see [LICENSE](LICENSE).
