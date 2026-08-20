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

## ⚡ How to Start the Services (local dev, without Docker)

Ensure you start the services in the following order. This path runs each service as a plain local process — it does **not** use `docker-compose.yml` (that's the production path, see below); mixing the two will cause port collisions since compose also starts `ai-service`/`backend`/`frontend` containers on the same ports.

### 1. External Dependencies (PostgreSQL & Redis)
You need a local Postgres (with the `pgvector` extension) and Redis reachable at the ports in `backend/.env` (defaults: `5432`/`6379`). The quickest way is the two infra-only containers from `start_services.sh`, which use the same default ports so no `.env` edits are needed:
```bash
./start_services.sh
```
If you already have Postgres/Redis running locally on those ports, skip this script entirely.

### 2. AI Processing Microservice (`ai-service`)
This service runs OpenCV heuristics, EasyOCR, and InsightFace face-matching on port `8001`.
```bash
./start_ai_service.sh
```
First run downloads the InsightFace (`buffalo_l`, ~600MB) and EasyOCR (~95MB) model weights — this can take a few minutes and needs internet access. Verify it's actually up before moving on:
```bash
curl http://localhost:8001/docs
```

### 3. Backend Orchestrator (`backend`)
This service handles database storage, visitor profiles, venue statistics, and S3 uploads on port `8000`. Needs `backend/.env` populated (copy from `backend/.env.example`) — in particular `SECRET_KEY`, `S3_BUCKET_NAME`/AWS credentials or an `S3_ENDPOINT_URL` for local MinIO, and `AI_SERVICE_URL` (defaults to `http://localhost:8001`, correct as long as ai-service is running locally per step 2).
```bash
./start_backend.sh
```
Verify both the backend itself and its connection to Postgres/Redis/ai-service:
```bash
curl http://localhost:8000/health   # backend itself
curl http://localhost:8000/ready    # backend + db + redis + ai-service, each checked individually
```
If `/ready` reports `ai_service` as an error, ai-service either isn't running or `AI_SERVICE_URL` in `backend/.env` doesn't point at it — this is the single most common cause of "backend can't reach the AI service" locally.

### 4. Next.js Gate Dashboard (`frontend`)
This client dashboard interfaces with the backend and runs the user interface on port `3000`.
```bash
cd frontend/frontend
cp .env.example .env   # if you haven't already — sets NEXT_PUBLIC_API_URL
npm run dev
```
`NEXT_PUBLIC_API_URL` is read at server start (`src/lib/api.ts`'s `getApiBase()`) — if you change it, restart `npm run dev`, a hot-reload isn't enough. Leave it unset for local dev against a backend on the same machine; it falls back to `http://<hostname>:8000/api/v1` automatically.

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

## 🚀 Production Deployment (Docker Compose on EC2 t3.medium)

`db`, `redis`, `ai-service`, `backend`, and `frontend` run as containers defined in the root `docker-compose.yml`, sized to fit a **t3.medium (2 vCPU / 4GB RAM)**. Verification images go straight to real **S3** — there is no local object-storage container to run or back up. Total container memory limits (~3.1GB) leave headroom under 4GB for the host OS and Docker daemon; a 2GB swap file (provisioned by the bootstrap script below) is a backstop for transient spikes, not something the stack is expected to lean on.

**t3.medium is the minimum, not a suggestion.** `ai-service` alone (InsightFace + EasyOCR + PyTorch CPU) commonly needs 1.5-2.5GB of real memory once its models are loaded — it will not run on a `t3.micro`/`t2.micro` (1GB RAM) or `t3.small`/`t2.small` (2GB RAM) even with a large swap file added. Swap does not substitute for RAM here: an ML inference workload constantly touching its model weights will page-thrash on swap badly enough that requests time out rather than complete, which surfaces as `/ready` reporting `"ai_service": "error: All connection attempts failed"` even though the container is technically running — it's just too slow to ever answer within any reasonable timeout. If you're on a smaller instance and see that error, upgrading instance size (not touching config) is the fix.

t2/t3 instances are burstable — CPU credits, not just RAM, are the constraint. `ai-service` is pinned to 2 threads (`OMP_NUM_THREADS`/`ORT_NUM_THREADS`) so a single OCR/face-match request can't burn the whole credit balance and starve the API. If sustained verification volume is high enough to exhaust CPU credits regularly, move to an `t3.unlimited` mode instance or a non-burstable type (`m6i.large`) — the compose file and resource limits do not need to change.

### 1. Create the S3 bucket and IAM role
```bash
aws s3api create-bucket --bucket venuepass-verification-images-prod --region us-east-1
aws s3api put-bucket-encryption --bucket venuepass-verification-images-prod \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket venuepass-verification-images-prod \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-lifecycle-configuration --bucket venuepass-verification-images-prod \
  --lifecycle-configuration file://deploy/aws/s3-lifecycle.json

aws iam create-role --role-name venuepass-ec2-role \
  --assume-role-policy-document file://deploy/aws/ec2-trust-policy.json
aws iam put-role-policy --role-name venuepass-ec2-role \
  --policy-name venuepass-s3-access --policy-document file://deploy/aws/s3-iam-policy.json
aws iam create-instance-profile --instance-profile-name venuepass-ec2-profile
aws iam add-role-to-instance-profile --instance-profile-name venuepass-ec2-profile --role-name venuepass-ec2-role
```
No access keys are stored anywhere — `backend/services/storage_service.py` picks up credentials from this instance profile automatically via boto3's default credential chain.

Verification images are keyed into two prefixes inside the one bucket, not two buckets — `storage_service.py` handles this automatically:
- **`scans/unflagged/`** — every image starts here. Routine retention (the hourly cron and the `/admin/flush` endpoint) deletes freely from this prefix, and the bucket lifecycle rule above force-expires anything left here after 7 days.
- **`scans/flagged/`** — the moment a customer is blacklisted (auto-detected mid-verification, a manual BLOCK/RESTRICT decision, or a standalone ban against a past visitor), every image belonging to that customer — across all their past sessions — is moved here via `move_to_banned`/`quarantine_customer_images`. Nothing under `scans/flagged/` is ever touched by retention or `/admin/flush`, and the lifecycle rule has no expiration for this prefix — flagged customers' images are retained permanently, by design.

Because it's a prefix split within one bucket rather than two buckets, a bulk "wipe everything routine" operation is just `aws s3 rm s3://<bucket>/scans/unflagged/ --recursive` — `scans/flagged/` is structurally untouched by that command.

### 2. Launch the EC2 instance
- **Type**: `t3.medium`, Amazon Linux 2023 or Ubuntu 22.04+, ≥30GB gp3 root volume (the `ai-service` image with baked-in model weights is large).
- **IAM instance profile**: `venuepass-ec2-profile` from step 1.
- **Security group**: 22 (SSH, your IP only), 80/443 if fronting with a reverse proxy (recommended, see step 5) or 3000/8000 directly otherwise. Nothing else public — `docker-compose.yml` binds Postgres/Redis/ai-service to `127.0.0.1` so they're unreachable outside the box regardless.
- **User data**: paste [`deploy/aws/ec2-user-data.sh`](deploy/aws/ec2-user-data.sh) (edit `REPO_URL` at the top first). It installs Docker, adds a 2GB swap file, clones the repo, and registers a `venuepass.service` systemd unit so the stack restarts automatically after a reboot or `docker compose down`.

### 3. Configure secrets
SSH in and finish the `.env` the bootstrap script generated:
```bash
cd /opt/venuepass
$EDITOR .env   # set POSTGRES_PASSWORD, S3_BUCKET_NAME=venuepass-verification-images-prod,
               # and SEED_ADMIN_PASSWORD (see step 5 below)
```
`.env` is git-ignored — never commit it. If you're deploying behind a domain, also set `NEXT_PUBLIC_API_URL` to the backend's public URL (e.g. `https://api.yourdomain.com/api/v1`) — this is baked into the frontend at **build** time, so changing it later requires a rebuild (`docker compose build frontend`), not just a restart.

### 4. Build and start
```bash
docker compose up -d --build
```
First build downloads and bakes in the InsightFace (`buffalo_l`, ~600MB) and EasyOCR (~95MB) model weights during the `ai-service` image build — this makes the initial build slower but means containers start instantly afterward with no runtime internet dependency. Expect this to take longer on a t3.medium than on a beefier dev machine; it's a one-time cost per image rebuild.

### 5. Verify
```bash
docker compose ps                       # all services healthy
free -h                                  # confirm memory headroom under load
curl http://localhost:8000/health        # backend
curl http://localhost:8000/ready         # backend + db + redis + ai-service connectivity
curl http://localhost:8001/docs          # ai-service
curl http://localhost:3000               # frontend
```
Database tables are auto-created on backend startup, and a bootstrap `super_admin` account is seeded from `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` in `.env` (defaults: `admin@venuepass.local` / `ChangeMe123!` — see `backend/seed.py`, run via the backend service's `command:` in `docker-compose.yml` before uvicorn starts). **Set a real `SEED_ADMIN_PASSWORD` in `.env` before deploying anywhere reachable from outside your own machine** — the default is a documented value, not a secret. The seed is idempotent (only creates the account if that email doesn't already exist), so changing the password in `.env` after first boot won't retroactively update an already-created account; log in and change it from the Staff Accounts admin page instead, or update it directly in Postgres.

### 6. Put a reverse proxy in front (recommended)
For a real domain with HTTPS, put [Caddy](https://caddyserver.com/) (or nginx + certbot) in front of ports 3000 (frontend) and 8000 (backend). A minimal `Caddyfile`:
```
yourdomain.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy /* localhost:3000
}
```
Caddy handles Let's Encrypt certificate issuance/renewal automatically. Caddy itself is lightweight enough to run directly on the same t3.medium alongside the compose stack.

### Notes
- **Data retention**: expired visitor records are anonymized automatically every hour (configurable per-venue via the venue config API, 7-day default after a PASS decision). Admins can trigger it manually and view the audit log from Settings in the web console. The bucket lifecycle rule from step 1 is a backstop that expires `scans/unflagged/` objects after 7 days regardless — flagged customers' images (`scans/flagged/`) are exempt from both the cron and the lifecycle rule, by design.
- **Resource limits**: every service in `docker-compose.yml` has a `deploy.resources.limits.memory` cap so one runaway container (most likely `ai-service` under burst load) can't OOM the whole box; Docker will restart a container that hits its cap rather than letting the kernel OOM-killer pick a victim.
- **Restart on reboot**: `restart: unless-stopped` handles container crashes, but a full instance reboot needs the Docker daemon to come up and then `docker compose up` to run again — that's what the `venuepass.service` systemd unit from the bootstrap script does. Verify it after first boot with `systemctl status venuepass`.
- **`start_services.sh`** (podman-based, Postgres+Redis only, standard ports) is superseded by `docker-compose.yml` for production; kept only for local non-Docker development.
- Not verified end-to-end in this development sandbox (no Docker daemon or AWS credentials available here) — run `docker compose config` locally and a real `docker compose up -d --build` on the target EC2 instance to confirm the build and S3 connectivity succeed there.

---

## ☁️ Alternative: ECS/Fargate + RDS (multi-instance scale-out)

The single-VM t3.medium setup above is the recommended starting point. If verification volume outgrows one instance, `backend` and `ai-service` are two independently deployable, stateless containers (each has its own `Dockerfile`) that fit ECS/Fargate services behind an ALB, with managed AWS services standing in for the containers that only exist for convenience in `docker-compose.yml` (`db` → RDS, `redis` → ElastiCache). S3 setup is identical to step 1 above — the same bucket and IAM policy work for both deployment styles.

### 1. S3 (object storage for verification images)
```bash
aws s3api create-bucket --bucket venuepass-verification-images-prod --region us-east-1
aws s3api put-bucket-encryption --bucket venuepass-verification-images-prod \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket venuepass-verification-images-prod \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```
Add a lifecycle rule to auto-expire objects (verification images are already deleted by the retention cron via the API, but a bucket-level backstop is good practice):
```bash
aws s3api put-bucket-lifecycle-configuration --bucket venuepass-verification-images-prod \
  --lifecycle-configuration file://deploy/aws/s3-lifecycle.json
```

The backend talks to S3 via `boto3` (`backend/services/storage_service.py`). **Do not put access keys in the container** — attach the IAM policy in [`deploy/aws/s3-iam-policy.json`](deploy/aws/s3-iam-policy.json) to the ECS **task role** (not the task execution role) and boto3 picks up credentials automatically from the container's IAM identity. Only set these two env vars on the backend task/service:
```
S3_BUCKET_NAME=venuepass-verification-images-prod
AWS_REGION=us-east-1
```
Leave `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` **unset** in AWS — those exist only so the same code can target an S3-compatible endpoint (e.g. MinIO) for local development outside Docker.

### 2. RDS (Postgres) and ElastiCache (Redis)
Provision an RDS PostgreSQL instance (`pgvector` extension: use RDS Postgres 15+ and run `CREATE EXTENSION vector;` once, or use Aurora PostgreSQL which bundles it) and an ElastiCache Redis cluster in the same VPC as the ECS tasks. Set on the backend task:
```
DATABASE_URL=postgresql+psycopg2://user:pass@your-instance.xxxx.rds.amazonaws.com:5432/pub_entry_db
REDIS_URL=redis://your-cluster.xxxx.cache.amazonaws.com:6379/0
```
(`DATABASE_URL` overrides the individual `POSTGRES_*` vars — see `backend/core/config.py`.)

### 3. ECS services
- **`ai-service`**: CPU-bound (EasyOCR + InsightFace ONNX inference) — no external state, no IAM permissions needed. Size the task for at least 2 vCPU / 4GB; model weights are baked into the image at build time (see `ai-service/Dockerfile`), so cold start has no internet dependency.
- **`backend`**: give it the S3 task role above, plus network access to RDS/ElastiCache. Set `AI_SERVICE_URL` to the `ai-service` ECS service's internal address — either Cloud Map service-discovery DNS (`http://ai-service.internal:8001`) or an internal ALB/NLB in front of it. **This must not be `localhost`** in ECS, since each service is a separate task.
- Both images expose a container `HEALTHCHECK` (`/health` on the backend, `/docs` on ai-service) and the backend additionally exposes `/ready` for ALB target-group health checks that verify DB/Redis/AI-service connectivity end-to-end.
- Push both images to ECR:
  ```bash
  aws ecr create-repository --repository-name venuepass-backend
  aws ecr create-repository --repository-name venuepass-ai-service
  docker build -t venuepass-backend -f backend/Dockerfile .
  docker build -t venuepass-ai-service ai-service/
  # tag + docker push to each repo's ECR URI
  ```

### 4. Secrets
Put `SECRET_KEY`, `POSTGRES_PASSWORD`/`DATABASE_URL`, and `REDIS_URL` in AWS Secrets Manager or SSM Parameter Store and reference them from the ECS task definition's `secrets` block — do not bake them into the image or set them as plain task-definition environment variables.

### 5. Frontend
Deploy the Next.js frontend to its own ECS service (or Amplify/CloudFront+S3 for a purely static export) with `NEXT_PUBLIC_API_URL` set to the backend ALB's public HTTPS URL at **build** time.
