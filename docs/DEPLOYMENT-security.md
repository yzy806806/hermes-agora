# Security — Agora Deployment

## 8. TLS Termination

The coordinator serves HTTP. Use a reverse proxy for TLS in production.

### Caddy (Recommended — Auto-Cert)

```Caddyfile
agora.example.com {
    reverse_proxy localhost:8000
}
```

Caddy auto-provisions and renews Let's Encrypt certificates.

### Nginx + Certbot

```nginx
server {
    listen 443 ssl http2;
    server_name agora.example.com;
    ssl_certificate /etc/letsencrypt/live/agora.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/agora.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## JWT Secret Rotation

1. Generate: `openssl rand -hex 32`
2. Update `AGORA_JWT_SECRET` in environment
3. Restart: `docker compose restart coordinator`
4. All existing tokens invalidated — agents re-register

Schedule rotation every 90 days. Use a secrets manager (Vault, AWS SSM).

## RBAC Configuration

Set `AGORA_RBAC_ENFORCE=true` to enable role-based access control.

| Role | Permissions |
|------|-------------|
| `admin` | All (full system access) |
| `agent` | Discussion, task, review, register, config:read |
| `observer` | Discussion, vote, config:read only |

Without `AGORA_RBAC_ENFORCE`, `@requires` is a no-op (backward compat).

## Agent Token Management

When `AGORA_REQUIRE_APPROVAL=true`, new agents need approval:

1. Agent calls `POST /api/v1/agents/register` → status `pending`
2. Admin calls `POST /api/v1/admin/agents/{agent_id}/approve`
3. Agent receives token for subsequent requests

For automated deployments, set `AGORA_ADMIN_TOKEN` to auto-approve.

## Dashboard Authentication

Set `AGORA_DASHBOARD_USERS` for basic auth:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'mypass', bcrypt.gensalt()).decode())"
AGORA_DASHBOARD_USERS="admin:$2b$12$..."
```
