# Auto-Pentest — Recon & Vulnerability Scanner

Automated reconnaissance and vulnerability scanning (nmap, subfinder, httpx,
katana, feroxbuster, nuclei) with a web dashboard, live scan progress, Redis
caching, scan history, and downloadable PDF reports.

## Run it on any PC (no source code needed)

You only need **Docker** installed and running, plus the launcher script for
your OS. The script pulls the 4 images from Docker Hub and wires them together.

**Windows:**
```
run.bat
```

**Linux / macOS:**
```
chmod +x run.sh stop.sh
./run.sh
```

Then open **http://localhost:3000**.

To stop everything (data is preserved): `stop.bat` (Windows) or `./stop.sh`.

> Prefer Docker Compose? A `docker-compose.yml` is included too —
> `docker compose up -d` does the same thing.

## The images (on Docker Hub)

| Component | Image |
|-----------|-------|
| Scanner API (FastAPI + tools) | `salamaaa11/auto-pentest-scanner:latest` |
| Frontend (Next.js) | `salamaaa11/auto-pentest-frontend:latest` |
| Database | `salamaaa11/auto-pentest-mongodb:latest` |
| Cache | `salamaaa11/auto-pentest-redis:latest` |

All are also tagged `:v1`.

## Requirements & notes

- **CPU:** x86_64 / amd64. (The re-hosted mongo/redis images are amd64-only; on
  Apple Silicon use the official `mongo:6.0` / `redis:7-alpine` instead.)
- **Ports used on the host:** 3000 (frontend), 8000 (API), 27017 (Mongo), 6379 (Redis).
- **Browse from the same PC** that runs the containers. The frontend is built
  with `API_URL=http://localhost:8000`; to use it from another machine, rebuild
  the frontend image with that host's address.
- **Internet** is required to scan external targets.

## Usage

1. Open http://localhost:3000
2. Enter a target — IP (`45.33.32.156`), CIDR (`192.168.1.0/24`), domain
   (`example.com`), or URL (`https://site.com`).
3. Click **Lancer**. The console streams each tool's progress live.
4. View results in the metric cards + vulnerability table; open the **Logs** tab
   for scan history; click **Rapport complet** to download a PDF report.

### Tuning (scanner environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `NMAP_TOP_PORTS` | `1000` | How many top ports nmap scans |
| `NMAP_PORTS` | *(unset)* | Exact port spec, e.g. `1-65535` for a full scan |
| `NMAP_TIMING` | `-T4` | nmap timing template |
| `SCAN_CACHE_TTL` | `3600` | Cache lifetime (seconds) for repeated scans |
