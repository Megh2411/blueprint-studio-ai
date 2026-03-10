# System Architecture & Technical Flow 🏗️📊

This document details the system design, communication protocols, database schema, and end-to-end data flow of **Blueprint Studio AI**.

---

## 🗺️ 1. System Components & Networking

The system is split into three main decoupled layers:
1.  **Client Tier (Frontend)**: React (Vite) application rendering the canvas editor, setting sliders, and displaying real-time telemetry metrics and gallery updates.
2.  **API Tier (FastAPI)**: Handlers for prompt optimization, job submission, WebSocket connection routing, and history fetching.
3.  **Task Worker Tier (Celery + Redis)**: Out-of-band asynchronous processing for heavy computation (AI model invocation, image metrics calculation).

```mermaid
graph TD
    Client[React Frontend] <-->|HTTP / WebSockets| API[FastAPI Web Server]
    API <-->|SQLAlchemy ORM| DB[(Supabase PostgreSQL)]
    API --->|Push Task| Queue[(Upstash Redis Broker)]
    Queue --->|Fetch Task| Worker[Celery Background Worker]
    Worker --->|SQLAlchemy Update| DB
    Worker --->|Upload Image| Storage[(Supabase Storage Buckets)]
    Worker --->|Optimize / Score| Gemini[Gemini 2.5 Flash API]
    Worker --->|Denoise Latents| HF[Hugging Face FLUX API]
```

---

## 🔄 2. End-to-End Execution Lifecycle

The lifecycle of an image generation run is managed as follows:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as React Frontend
    participant BE as FastAPI API Server
    participant Celery as Celery Worker
    participant DB as Supabase DB
    participant HF as Hugging Face / Gemini

    User->>FE: Sketch layout & Enter Prompt
    User->>FE: Click "Execute Run"
    FE->>BE: POST /api/renders (Prompt, Base64 Sketch, Hyperparameters)
    Note over BE: Generate UUID for Job
    BE->>DB: Insert Job (Status = Pending)
    BE->>Celery: trigger process_render_job.delay(job_id, params)
    BE-->>FE: Return Job UUID (HTTP 202 Accepted)
    
    activate Celery
    Celery->>DB: Update Status = Processing
    Celery->>HF: Call Image-to-Image Pipeline (Denoising & Prompts)
    HF-->>Celery: Return Rendered PIL Image
    Celery->>DB: Upload PIL bytes to Supabase Storage
    Celery->>HF: Send Rendered Image to Gemini for Semantic Evaluation
    HF-->>Celery: Return CLIP Score
    Celery->>Celery: Compute local SSIM (NumPy array comparison)
    Celery->>DB: Update Job (Status = Completed, Render URL, Metrics)
    deactivate Celery
    
    Celery->>BE: Trigger WebSocket callback notification
    BE->>FE: WebSocket message: {status: 'completed', render_path: 'url', metrics: {...}}
    FE->>FE: Update main render view and trigger Gallery refetch
```

---

## 🗄️ 3. Database Entity-Relationship (ER) Schema

The application uses two principal relational tables. Direct UUID casting is enforced throughout to guarantee compatibility with PostgreSQL.

### Users Table (`users`)
Keeps track of unique client IDs (frictionless browser-assigned sessions).
*   `id`: `UUID` (Primary Key, Defaults to `uuid_generate_v4()`)
*   `created_at`: `TIMESTAMP WITH TIME ZONE`

### Render Jobs Table (`render_jobs`)
Stores generation parameters, inputs, generated assets, and real-time metrics.
*   `job_id`: `UUID` (Primary Key, Defaults to `uuid_generate_v4()`)
*   `user_id`: `UUID` (Foreign Key -> `users.id`)
*   `prompt`: `TEXT`
*   `sketch_path`: `TEXT` (Public Supabase storage URL of the drawn canvas sketch)
*   `render_path`: `TEXT` (Public Supabase storage URL of the AI output)
*   `status`: `VARCHAR(50)` (Pending, Processing, Completed, Failed)
*   `control_strength`: `DOUBLE PRECISION` (Denoising strength factor)
*   `steps`: `INTEGER` (Denoising steps)
*   `cfg_scale`: `DOUBLE PRECISION` (Classifier-Free Guidance scale)
*   `metrics`: `JSONB` (Stores `ssim` and `clipScore` keys)
*   `created_at`: `TIMESTAMP WITH TIME ZONE`

---

## 📡 4. WebSocket Connection State Management

*   **Endpoint**: `ws://127.0.0.1:8000/ws/{client_uuid}`
*   Upon loading the page, the frontend establishes a persistent connection.
*   The API server maps active connection connections in a thread-safe `ConnectionManager` dictionary: `{ client_uuid: WebSocket }`.
*   When a background worker finishes a rendering task, it sends an update request or direct callback notifying the corresponding WebSocket channel.
*   If a user closes the browser or disconnects, the API server cleanly removes their socket from memory to prevent memory leaks.
