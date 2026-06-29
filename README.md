# 🛡️ Pub Entry Security & ID Verification Pipeline

Welcome to the Pub Entry and ID Verification System. This project provides an automated, high-fidelity security gateway for venues to scan UK Driving Licences, extract visitor details, calculate risk factors, and determine authenticity (Genuine vs. Fake) using advanced spatial parsing and computer vision heuristics.

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
