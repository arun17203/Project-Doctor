# Project Doctor — Production Deployment Checklist

Use this checklist before releasing or hosting Project Doctor on cloud platforms (AWS, DigitalOcean, GCP, Render, Azure, or on-premises servers).

---

## 1. Environment & Secrets Configuration

- [ ] **Generate Production Secret Key**:
  ```bash
  openssl rand -hex 32
  ```
  Set `SECRET_KEY` in production `.env` (min 32 characters).
- [ ] **Disable Debug Mode**:
  Ensure `DEBUG=False` and `ENVIRONMENT=production`.
- [ ] **Database Connection String**:
  Set `DATABASE_URL` to a persistent PostgreSQL 16+ instance:
  ```env
  DATABASE_URL="postgresql://user:password@hostname:5432/project_doctor"
  ```
- [ ] **Configure Allowed Origins**:
  Set `CORS_ORIGINS` to the exact public frontend domain(s):
  ```env
  CORS_ORIGINS="https://doctor.yourdomain.com"
  ```
- [ ] **Google Gemini API Key (Optional)**:
  Configure `GEMINI_API_KEY` for AI Explainer and Codebase Q&A features.
- [ ] **Storage Sandbox Mount**:
  Ensure `STORAGE_DIR` points to a persistent volume with read/write permissions for user `appuser` (UID 1000).

---

## 2. Database Migration & Schema Verification

- [ ] **Execute Alembic Migrations**:
  ```bash
  alembic upgrade head
  ```
- [ ] **Verify Table Creation**:
  Confirm all 16 domain tables (`users`, `projects`, `project_scans`, `project_files`, `quality_analyses`, `security_analyses`, `dependency_analyses`, `architecture_analyses`, `health_analyses`, `project_analysis_snapshots`, etc.) exist in the target database.

---

## 3. Container & Healthcheck Verification

- [ ] **Build Docker Containers**:
  ```bash
  docker compose build --no-cache
  ```
- [ ] **Verify Non-Root User**:
  Ensure `docker compose exec backend whoami` outputs `appuser`.
- [ ] **Verify Liveness & Readiness Probes**:
  ```bash
  curl -I http://localhost:8000/health
  # Expected: HTTP/1.1 200 OK -> {"status": "ok"}

  curl -I http://localhost:8000/health/ready
  # Expected: HTTP/1.1 200 OK -> {"status": "ready", "database": "connected"}
  ```

---

## 4. Reverse Proxy, SSL, & Nginx

- [ ] **Configure TLS/SSL**:
  Set up Let's Encrypt / Certbot or Cloudflare SSL termination.
- [ ] **Set Upload Body Limit**:
  Ensure `client_max_body_size 50M;` is active in Nginx or ingress controller to permit project ZIP uploads.
- [ ] **Security Headers Active**:
  Verify `X-Frame-Options`, `X-Content-Type-Options`, and `Referrer-Policy` response headers are returned.

---

## 5. Automated Testing Sign-off

- [ ] Backend tests passing: `pytest backend/tests -v` (95+ tests passed).
- [ ] Frontend tests passing: `npm test` in `frontend/` (all component tests passed).
- [ ] Frontend production bundle builds without errors: `npm run build`.
