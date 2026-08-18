# 🛡️ VenuePass — Venue Identity Verification Platform

Welcome to VenuePass. This project provides an automated, high-fidelity security gateway for venues to scan UK Driving Licences, extract visitor details, calculate risk factors, and determine authenticity (Genuine vs. Fake) using advanced spatial parsing and computer vision heuristics.

---

## 📂 Project Architecture

The codebase is split into three main components:

```
pub-entry/
├── ai-service/             # FastAPI - Computer Vision & OCR Microservice
│   ├── app/
│   │   ├── api/            # API routing & pipeline definition
│   │   ├── schemas/        # Request & Response model definitions
│   │   └── services/       # Core AI & OpenCV logic
│   │       ├── ocr/        # EasyOCR implementation & UK Driving Licence spatial parser
│   │       ├── image_quality.py         # Image resolution/blur/lighting analysis
│   │       ├── document_authenticity.py # Specular glare, print noise, and microtext heuristics
│   │       └── risk_engine.py           # Multi-factor risk calculation
│   └── venv/               # AI service python environment
│
├── backend/                # FastAPI - Main Web Backend Orchestrator
│   ├── app/
│   │   ├── models/         # Database models (SQLite via SQLAlchemy)
│   │   ├── api/            # Endpoint logic (blacklists, visits, memberships)
│   │   └── main.py         # Entry point for backend orchestrator (Port 8000)
│   └── venv/               # Backend python environment
│
├── frontend/
│   └── frontend/           # Next.js (React) - Security Gate Dashboard
│       ├── src/
│       │   ├── app/        # Next.js pages & app layout (Dashboard, Visitors, Incidents)
│       │   └── lib/        # State store (Zustand) & API connection utilities
│       └── package.json
│
├── docker-compose.yml      # Docker services (PostgreSQL & Redis)
└── pub_entry.db            # SQLite database file (Local development storage)
```

---

## ⚡ How to Start the Services

Ensure you start the services in the following order:

### 1. External Dependencies (PostgreSQL & Redis)
If your configuration uses PostgreSQL/Redis, bring them up via Docker Compose:
```bash
docker compose up -d
```

### 2. AI Processing Microservice (`ai-service`)
This service runs OpenCV heuristics and EasyOCR extraction on port `8001`.
```bash
cd ai-service
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. Backend Orchestrator (`backend`)
This service handles database storage, visitor profiles, and venue statistics on port `8000`.
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Next.js Gate Dashboard (`frontend`)
This client dashboard interfaces with the backend and runs the user interface on port `3000`.
```bash
cd frontend/frontend
npm run dev
```

---

## 🧠 Key Features & Technical Details

### 1. Spatial OCR Extraction (`UKDrivingLicenceProcessor`)
*   **Bounding-Box Sorting:** Sorts raw OCR texts by physical coordinate alignment (top-to-bottom, left-to-right) rather than reading order.
*   **Safe Next-Box Lending:** Automatically borrows values from adjacent coordinates if labels (e.g., `4b.`) are detached from values (e.g., `19.12.2035`), guarded by label-detection rules to prevent name/date overlap.
*   **DVLA License Formula Matching:** Uses structural patterns (16 characters) and translates alphanumeric anomalies (e.g., `O` to `0`, `I` to `1`) using DVLA-defined checksum formats.

### 2. OpenCV Authenticity & Risk Verification
We evaluate 2D images for signs of a "Fake Licence" based on 3 distinct visual matrices:
*   **Holograms & Material (Polycarbonate Glare):** Checks the HSV spectrum for high-exposure, low-saturation specular reflections typical of polycarbonate overlays.
*   **Microtext & Text Texture (High-Frequency Details):** Runs a Laplacian variance filter over text areas to detect blurry desktop printing versus sharp laser engraving.
*   **Print Quality (Lithographic vs. Desktop):** Employs Gaussian Blur subtraction to identify pixel dithering and print banding.

---

## 🚀 Production Deployment (Docker Compose, single VM)

All four services (`db`, `redis`, `minio`, `ai-service`, `backend`, `frontend`) are defined in the root `docker-compose.yml`. This is the recommended way to run the full stack on a single cloud VM.

### 1. Provision a VM and install Docker
Any VM with Docker + the Compose plugin works (e.g. a $20-40/mo 4 vCPU / 8GB RAM instance — the AI service, mainly EasyOCR + InsightFace CPU inference, is the heaviest consumer). Install Docker via your provider's guide or [docs.docker.com](https://docs.docker.com/engine/install/).

### 2. Configure secrets
```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD, and SECRET_KEY.
# Generate a real SECRET_KEY with:
openssl rand -hex 32
```
`.env` is git-ignored — never commit it. If you're deploying behind a domain, also set `NEXT_PUBLIC_API_URL` to the backend's public URL (e.g. `https://api.yourdomain.com/api/v1`) — this is baked into the frontend at **build** time, so changing it later requires a rebuild (`docker compose build frontend`), not just a restart.

### 3. Build and start
```bash
docker compose up -d --build
```
First build downloads and bakes in the InsightFace (`buffalo_l`, ~600MB) and EasyOCR (~95MB) model weights during the `ai-service` image build — this makes the initial build slower but means containers start instantly afterward with no runtime internet dependency.

### 4. Verify
```bash
docker compose ps                       # all services healthy
curl http://localhost:8000/health        # backend
curl http://localhost:8001/docs          # ai-service
curl http://localhost:3000               # frontend
```
Database tables are auto-created on backend startup, and a bootstrap `super_admin` account (`admin@pub-entry.local`) is auto-seeded with a random password printed once to the backend container logs (`docker compose logs backend | grep "Bootstrap super_admin"`) — log in with it immediately and create real staff accounts via the Staff Accounts admin page, since self-registration is disabled by design.

### 5. Put a reverse proxy in front (recommended)
For a real domain with HTTPS, put [Caddy](https://caddyserver.com/) (or nginx + certbot) in front of ports 3000 (frontend) and 8000 (backend). A minimal `Caddyfile`:
```
yourdomain.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy /* localhost:3000
}
```
Caddy handles Let's Encrypt certificate issuance/renewal automatically.

### Notes
- **Data retention**: expired visitor records are anonymized automatically every hour (configurable per-venue via the venue config API, 7-day default after a PASS decision). Admins can trigger it manually and view the audit log from Settings in the web console.
- **`start_services.sh`** (podman-based, ports 5433/6380) is superseded by `docker-compose.yml` for production; kept only for local non-Docker development.
- Not verified end-to-end in this development sandbox (no Docker daemon available here) — run `docker compose config` and a real `docker compose up -d --build` on your target VM/machine to confirm the build succeeds there.
