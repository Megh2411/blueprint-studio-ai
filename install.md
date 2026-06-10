# Installation & Environment Setup Guide 🛠️

Follow these instructions to configure and install all dependencies for **Blueprint Studio AI** from scratch.

---

## 📋 Prerequisites

Ensure you have the following software installed on your machine:
*   **Python**: Version `3.10` or higher
*   **Node.js**: Version `18.x` or higher & `npm`
*   **Redis**: Local Redis server or a cloud Redis instance (e.g., [Upstash Redis](https://upstash.com))
*   **Supabase Account**: A free database and storage project (PostgreSQL + S3 Bucket)

---

## 🗄️ Backend Setup (Python + FastAPI)

1.  **Navigate to the backend directory**:
    ```bash
    cd backend
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment**:
    *   **Windows**:
        ```powershell
        .\venv\Scripts\Activate.ps1
        ```
    *   **macOS / Linux**:
        ```bash
        source venv/bin/activate
        ```

4.  **Install requirements**:
    ```bash
    pip install -r requirements.txt
    ```
    *   *Note: For Windows background tasks, make sure to also install Eventlet:*
        ```bash
        pip install eventlet
        ```

5.  **Create your Environment File (`.env`)**:
    Create a file named `.env` in the `backend/` directory and configure the variables:
    ```env
    # Supabase PostgreSQL Connection String
    DATABASE_URL="postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres"

    # Supabase Client Settings (For public storage URLs)
    SUPABASE_URL="https://[project-id].supabase.co"
    SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5..."

    # Redis Task Broker URL
    REDIS_URL="redis://default:[password]@[endpoint]:6379"

    # API Keys for AI Models
    GEMINI_API_KEY="AIzaSy..."
    HUGGINGFACE_API_KEY="hf_..."
    ```

---

## 🎨 Frontend Setup (React + Vite)

1.  **Navigate to the frontend directory**:
    ```bash
    cd ../frontend
    ```

2.  **Install Node packages**:
    ```bash
    npm install
    ```

---

## 🏛️ Database Schema Setup (PostgreSQL)

If your database tables are not initialized, execute the following SQL scripts in the **Supabase SQL Editor** to set up the schema and create the necessary tables:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create Users Session table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Render Jobs table
CREATE TABLE IF NOT EXISTS render_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    prompt TEXT NOT NULL,
    sketch_path TEXT NOT NULL,
    render_path TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    control_strength FLOAT DEFAULT 0.7,
    steps INT DEFAULT 25,
    cfg_scale FLOAT DEFAULT 7.0,
    metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create storage bucket policy (Enable public read access for bucket "renders")
-- Make sure to create a public bucket named "renders" inside Supabase Storage console.
```

---

## 🛠️ Supabase Storage Configuration

1.  Open the **Supabase Dashboard** -> **Storage**.
2.  Click **New Bucket** and name it `renders`.
3.  Set the bucket visibility to **Public**.
4.  Add a storage policy allowing **Insert** and **Select** operations for all users so the backend API and worker can upload files.
