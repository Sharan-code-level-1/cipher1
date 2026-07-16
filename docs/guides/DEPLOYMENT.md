# Deployment Guide

## Local (Docker Compose)

```bash
cp .env.example .env
# set SECRET_KEY and AES_MASTER_KEY
docker compose up --build -d
```

Services:
- http://localhost (NGINX)
- http://localhost:8000/docs (API)
- http://localhost:5555 (Flower)
- http://localhost:8025 (Mailhog)

## Production checklist

1. Generate strong `SECRET_KEY` and `AES_MASTER_KEY`
2. Use managed PostgreSQL and Redis
3. Put object storage (S3/GCS) behind File Storage service
4. Terminate TLS at load balancer / NGINX
5. Disable debug; restrict CORS origins
6. Run Alembic migrations as a release job
7. Configure real SMTP/SMS providers
8. Enable virus scanning
9. Ship logs/metrics to SIEM/APM
10. Restrict admin networks if required

## Scaling

- Horizontally scale `backend` and `worker`
- Keep sticky sessions unnecessary (JWT)
- Use shared storage for uploads
