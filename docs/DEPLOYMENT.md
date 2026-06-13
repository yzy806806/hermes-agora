# Agora Deployment Guide

> Covers production multi-tenant deployment with Docker Compose.

## Sub-documents

| File | Topic |
|------|-------|
| [DEPLOYMENT-config.md](DEPLOYMENT-config.md) | Configuration, env vars, tenant setup |
| [DEPLOYMENT-ops.md](DEPLOYMENT-ops.md) | Backup, monitoring, troubleshooting |
| [DEPLOYMENT-scaling.md](DEPLOYMENT-scaling.md) | Scaling and performance |
| [DEPLOYMENT-security.md](DEPLOYMENT-security.md) | TLS, JWT, RBAC, agent tokens |

---

## 1. Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 20.10+ | 24+ |
| Docker Compose | v2.0+ | v2.20+ |
| RAM | 1 GB | 2 GB |
| Disk | 5 GB | 20 GB (depends on data) |
| Domain | — | For TLS termination |

DNS: point your domain (e.g. `agora.example.com`) to the host IP before
starting.

TLS cert: use Caddy (auto-cert) or nginx + Let's Encrypt (certbot).
See [DEPLOYMENT-security.md](DEPLOYMENT-security.md).

## 2. Quick Start

```bash
# Clone and enter the repo
git clone https://github.com/yzy806806/agora.git
cd agora

# Set required secret
export AGORA_JWT_SECRET=$(openssl rand -hex 32)

# Start production stack
docker compose -f docker-compose.prod.yaml up -d

# Verify health
curl http://localhost:8000/api/v1/health
# → {"status":"healthy","version":"0.13.0","uptime_seconds":3,...}
```

### Stop / Cleanup

```bash
docker compose -f docker-compose.prod.yaml down     # stop, keep data
docker compose -f docker-compose.prod.yaml down -v   # stop + delete volumes
```
