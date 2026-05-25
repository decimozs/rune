# Deployment Guide

## Option 1: Docker Compose (Single Machine)

This is the simplest deployment — everything runs on one machine using Docker.

```bash
# Clone the repository
git clone <repo-url> exist-ocr
cd exist-ocr

# Copy and edit configuration
cp .env.example .env
# Edit .env with your settings (at minimum: set OCR_API_KEYS)

# Start all services
docker compose up -d

# Verify everything is running
docker compose ps
```

All three services start:

| Service | Internal Port | External Port |
|---|---|---|
| OCR API | 80 | 8000 |
| nginx (images) | 80 | 8080 |
| Gotenberg | 3000 | 3000 |

Data persists in Docker volumes:

- `ocr_assets` — page images and markdown output files
- `ocr_data` — SQLite database (API keys)
- `paddle_models` — downloaded OCR model files (large, cached to avoid re-download)

### Updating

```bash
git pull
docker compose build ocr
docker compose up -d
```

### Backup

```bash
# Back up the database (API keys)
docker run --rm -v exist-ocr_ocr_data:/data -v $(pwd):/backup alpine \
  cp -r /data/ocr.db /backup/ocr.db.backup

# Back up any output files still within TTL
docker run --rm -v exist-ocr_ocr_assets:/data -v $(pwd):/backup alpine \
  tar czf /backup/assets-backup.tar.gz -C /data .
```

## Option 2: Azure VM

Deploy to an Azure Linux virtual machine.

### Prerequisites

1. An Azure VM with Ubuntu 22.04 LTS (Standard D2s v3 or larger — 2+ vCPUs, 8GB+ RAM recommended)
2. Docker and Docker Compose installed on the VM
3. SSH access to the VM
4. Ports 8000 and 8080 open in the Network Security Group

### Setup Script

SSH into the VM and run:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Log out and back in for Docker permissions to apply
exit
```

SSH back in, then:

```bash
# Clone the repository
git clone <repo-url> exist-ocr
cd exist-ocr

# Configure
cp .env.example .env
nano .env
# Set OCR_API_KEYS=sk-prod-key=admin
# Set OCR_DB_PATH=/app/data/ocr.db
# Set OCR_GOTENBERG_URL=http://gotenberg:3000

# Start services
docker compose up -d

# Verify
curl http://localhost:8000/health
curl http://localhost:8080/assets/  # should return 404 (not 502) — nginx is running
```

### Azure-Specific Considerations

| Aspect | Recommendation |
|---|---|
| **VM Size** | Start with D2s v3 (2 vCPU, 8GB RAM). Monitor memory usage |
| **Disk** | Use Premium SSD for OS disk. Output files are ephemeral (1hr TTL) |
| **Networking** | Restrict inbound ports to your company IP range in NSG rules |
| **Backups** | Back up `/app/data/ocr.db` regularly (API keys). Output files are auto-cleaned |
| **Monitoring** | Enable Azure Monitor for VM metrics. The app exposes `/health` for load balancer probes |
| **Scaling** | For higher throughput, use a larger VM or run multiple instances behind Azure Load Balancer |

### Setting Up Systemd (Auto-Restart)

Create `/etc/systemd/system/docker-compose-ocr.service`:

```ini
[Unit]
Description=OCR Pipeline Docker Compose
Requires=docker.service
After=docker.service

[Service]
WorkingDirectory=/opt/exist-ocr
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable docker-compose-ocr
sudo systemctl start docker-compose-ocr
```

## Option 3: Local Development (No Docker)

See the [Quick Start](02-quickstart.md) guide for local setup instructions.

## Environment Comparison

| Setting | Local Dev | Docker | Azure VM |
|---|---|---|---|
| `OCR_OUTPUT_DIR` | `app/outputs` | `/app/outputs` | `/app/outputs` |
| `OCR_ASSET_BASE_URL` | _(empty)_ | `http://localhost:8080` | `http://<vm-ip>:8080` |
| `OCR_GOTENBERG_URL` | `http://localhost:3000` | `http://gotenberg:3000` | `http://gotenberg:3000` |
| `OCR_DB_PATH` | `app/data/ocr.db` | `/app/data/ocr.db` | `/app/data/ocr.db` |
| Static files | FastAPI serves | nginx serves | nginx serves |
