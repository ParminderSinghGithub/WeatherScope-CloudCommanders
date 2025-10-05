Railway Deployment Guide for "Will It Rain on My Parade?"

Overview
--------
This repository contains a multi-service app (backend + frontend) orchestrated via `docker-compose.yml`.
Railway will use our compose configuration to build and deploy both services.

Key points
----------
- Railway uses nixpacks builder with Docker Compose support
- Both services (backend and frontend) are built from their respective Dockerfiles
- Keep secrets (like API keys) out of source code and in Railway environment variables

Before you deploy
-----------------
1. Confirm Dockerfiles exist and contain no `VOLUME` lines:
   - `backend/Dockerfile`
   - `frontend/Dockerfile`

2. Confirm `docker-compose.yml` uses build contexts that point to those Dockerfiles:
   - backend build context: `./backend`
   - frontend build context: `./frontend`

3. Create or ensure you have a Railway project and the Railway CLI installed: https://railway.app/

Add the API key in Railway
-------------------------
1. Open your project in the Railway web dashboard.
2. Go to "Variables" or "Environment" (name may vary).
3. Add a new variable:
   - Key: VC_API_KEY
   - Value: <your VisualCrossing API key>
   - Make sure it is marked as secret/private.

Railway Configuration
-------------------
The repository includes `railway.json` that configures the build and deployment:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "nixpacks",
    "buildCommand": "docker compose up"
  },
  "deploy": {
    "startCommand": "docker compose up",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "on_failure"
  }
}
```

This configuration:
- Uses Railway's nixpacks builder with Docker Compose support
- Runs `docker compose up` for both build and deploy
- Configures health checks and restart policy
- Automatically detects our multi-service setup via `docker-compose.yml`

Deploy using the CLI
--------------------
From the repository root (where `docker-compose.yml` lives) run:

    railway up

Railway will build both services using the Dockerfiles in their respective directories.

Troubleshooting
---------------
- Error: `dockerfile parse error: unknown instruction: version:` — you (or a script) tried to run `docker build` on the compose file. Stop and run `railway up` instead.
- Error: `Invalid input` with builder — make sure `railway.json` uses the correct builder configuration shown above.
- Error: `VOLUME` is banned — remove any `VOLUME` lines from Dockerfiles and rely on Railway-managed volumes if persistent storage is required.
- Missing env var at runtime — confirm `VC_API_KEY` exists in Railway dashboard.

Local testing tips
------------------
- You can still run compose locally with Docker Compose:

    docker compose up --build

  This will use your local Docker engine and the Dockerfiles.

- To test the backend locally without Railway env vars, set `VC_API_KEY` in your shell (PowerShell example):

    $env:VC_API_KEY = "your_api_key_here"
    uvicorn backend.main:app --reload --port 8000

Security
--------
Never commit API keys or secrets to the repository. Use Railway environment variables or another secure secret manager.

Contact
-------
If you need help deploying, provide the full terminal output and which command you ran so we can diagnose further.