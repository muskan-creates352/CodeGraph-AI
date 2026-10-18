# CodeGraph AI — Production Cloud Deployment Guide 🌐

This guide outlines how to deploy **CodeGraph AI** to public cloud platforms with a persistent **FalkorDB** database, **FastAPI** backend, and **React** frontend.

---

## Architecture Overview

```
[ User Browser ]
       |
       v
[ Vercel / Cloudflare Pages ] (Frontend SPA: React + Vite)
       |
       | HTTPS (/api/*)
       v
[ Render / Railway ] (Backend: FastAPI on Python 3.11)
       |
       | TCP / RESP (Port 6379)
       v
[ FalkorDB Cloud ] (Managed GraphBLAS Database: app.falkordb.cloud)
```

---

## 🚀 Recommended Approach: Free Tier Cloud-Native Setup

### Step 1: Spin Up a Managed FalkorDB Cloud Instance (Free)
1. Go to **[https://app.falkordb.cloud/](https://app.falkordb.cloud/)** and sign in with GitHub or Google.
2. Click **Create Database**.
3. Select the **Free Tier** instance.
4. Note your connection details:
   - **Host** (e.g. `instance-1234.falkordb.cloud`)
   - **Port** (e.g. `6379`)
   - **Password** (e.g. `xyz...`)

---

### Step 2: Deploy the FastAPI Backend to Render (Free)
1. Go to **[https://render.com/](https://render.com/)** and log in with GitHub.
2. Click **New +** $\rightarrow$ **Web Service**.
3. Select your repository: `muskan-creates352/CodeGraph-AI`.
4. Configure the service:
   - **Name:** `codegraph-ai-backend`
   - **Environment:** `Python 3`
   - **Root Directory:** (leave blank)
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `PYTHONPATH`: `backend`
   - `FALKORDB_HOST`: *(Your FalkorDB Cloud Host)*
   - `FALKORDB_PORT`: *(Your FalkorDB Cloud Port)*
   - `FALKORDB_PASSWORD`: *(Your FalkorDB Cloud Password)*
   - `FALKORDB_GRAPH_NAME`: `codegraph`
6. Click **Create Web Service**.  
   Render will deploy your backend at a public URL: `https://codegraph-ai-backend.onrender.com`.

---

### Step 3: Deploy the React Frontend to Vercel (Free)
1. Go to **[https://vercel.com/](https://vercel.com/)** and log in with GitHub.
2. Click **Add New...** $\rightarrow$ **Project**.
3. Import `muskan-creates352/CodeGraph-AI`.
4. Configure the build:
   - **Root Directory:** `frontend`
   - **Framework Preset:** `Vite`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
5. Under **Environment Variables**, add:
   - `VITE_API_BASE_URL`: `https://codegraph-ai-backend.onrender.com`
6. Click **Deploy**.  
   Vercel will output a live URL (e.g. `https://codegraph-ai.vercel.app`).

---

## 🐳 Alternative: Single Cloud Server Deployment (Docker Compose)

If deploying to a single Linux VM (AWS EC2, DigitalOcean Droplet, Hetzner):
1. Clone the repository:
   ```bash
   git clone https://github.com/muskan-creates352/CodeGraph-AI.git
   cd CodeGraph-AI
   ```
2. Build and launch services in background:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
3. Verify running containers:
   ```bash
   docker ps
   ```
   Both `falkordb-prod` and `codegraph-backend-prod` will run with auto-restart and isolated graph volumes.
