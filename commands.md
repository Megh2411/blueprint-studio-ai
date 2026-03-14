# Run & Execution Guide 💻

This document outlines the commands needed to run the entire **Blueprint Studio AI** application. 

Open three separate terminals to start the Backend API server, the Celery background worker, and the React frontend server.

---

## 🖥️ Terminal 1: Backend API Server (FastAPI)

Starts the main REST API and WebSocket gateway on `http://127.0.0.1:8000`.

### Windows (PowerShell / Command Prompt)
```powershell
# Navigate to backend directory
cd backend

# Activate Virtual Environment
.\venv\Scripts\Activate.ps1

# Run Uvicorn Development Server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### macOS / Linux
```bash
# Navigate to backend directory
cd backend

# Activate Virtual Environment
source venv/bin/activate

# Run Uvicorn Development Server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## ⚙️ Terminal 2: Celery Background Worker

Processes the image generation, metrics computation, and Supabase uploads asynchronously.

### Windows (PowerShell / Command Prompt)
> [!IMPORTANT]
> Celery does not natively support process pooling on Windows. You must install `eventlet` in your virtual environment and run Celery with the `-P eventlet` execution pool.

```powershell
# Navigate to backend directory
cd backend

# Activate Virtual Environment
.\venv\Scripts\Activate.ps1

# Start Celery Worker with Eventlet Pool
celery -A app.workers.tasks.celery_app worker --loglevel=info -P eventlet
```

### macOS / Linux
```bash
# Navigate to backend directory
cd backend

# Activate Virtual Environment
source venv/bin/activate

# Start Celery Worker
celery -A app.workers.tasks.celery_app worker --loglevel=info
```

---

## 🎨 Terminal 3: Frontend Web App (Vite + React)

Starts the hot-reloading development server on `http://localhost:5173`.

### All Platforms (Windows, macOS, Linux)
```bash
# Navigate to frontend directory
cd frontend

# Install Node modules (if not already installed)
npm install

# Start Vite Development Server
npm run dev
```

---

## 🧪 Terminal 4: Testing & Verification (Optional)

Scripts to verify backend connectivity, database models, and API endpoints.

```powershell
# Run E2E Database queries test
python backend/tests/test_e2e_db.py

# Run API endpoint generator test
python backend/tests/test_e2e_api.py
```
*(Make sure your virtual environment is active in this terminal prior to execution).*
