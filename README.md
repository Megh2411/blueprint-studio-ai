# Blueprint Studio AI 🎨🖌️

> **Iterative Sketch-to-Render Architecture Engine powered by Latent Diffusion, ControlNet, and LLM-Guided Prompt Refinement.**

Blueprint Studio AI is a state-of-the-art Web application tailored for architects, interior designers, and visual artists. It allows users to sketch layout outlines or upload reference structures, provide text prompts, and instantly generate hyper-realistic architectural designs. 

Powered by a hybrid pipeline utilizing **FLUX.1-schnell** (composition-accurate image-to-image/sketch guidance) and **Gemini 2.5 Flash** (agentic prompt mapping & visual scoring), the platform provides real-time telemetry metrics (Structural Similarity - SSIM and semantic CLIP score evaluation) for every generated render.

---

## 🌟 Key Features

*   **Interactive Sketching & Inpainting Canvas**: Draw structure outlines directly in the browser or load an inpainting mask to edit specific sections of your layout.
*   **Prompt Optimization (Magic Enhance)**: Refines raw user prompts into rich descriptive prompts using Gemini 2.5 Flash, adding atmospheric detail, lighting styles, and architectural textures.
*   **Composition-Accurate Render Engine**: Translates sketches into realistic images while respecting structure boundaries using FLUX.1.
*   **Iterative Design Cycle**: Load generated renders back into the canvas as sketch references with one click to edit, refine, or inpaint further.
*   **Real-time AI Telemetry**: 
    *   **SSIM (Structural Similarity Index)**: Measures structural fidelity between the original sketch and the final render.
    *   **Semantic Score (CLIP)**: Calculates prompt alignment using Gemini 2.5 Flash's vision API to score aesthetic correlation.
*   **Frictionless Session Management**: Uses browser-assigned client sessions, linking your history to PostgreSQL database records via Supabase without requiring forced user logins.
*   **Background Worker Queue**: Processes image generation tasks asynchronously using Celery and Redis to handle concurrent requests seamlessly.
*   **Interactive History Gallery**: Save, revisit, redraft, and download high-resolution renders of all past designs directly.

---

## 🛠️ Technology Stack

*   **Frontend**: React (Vite), Tailwind CSS, Lucide Icons
*   **Backend API**: FastAPI (Python), SQLAlchemy, WebSockets
*   **Task Queue**: Celery, Redis (Upstash)
*   **Database & Storage**: PostgreSQL & Storage Buckets (Supabase)
*   **Model Pipelines**:
    *   **Image Generation**: FLUX.1-schnell (Hugging Face serverless API)
    *   **Vision & Text LLM**: Google Gemini 2.5 Flash API

---

## 🚀 Quick Start

1.  **Clone & Install Dependencies**
    Read [install.md](file:///d:/Projects/blueprint-studio-ai/install.md) for full system configuration and dependency steps.
    
2.  **Environment Setup**
    Ensure backend `.env` variables are configured (Supabase keys, Redis endpoint, Gemini API key, and Hugging Face token).

3.  **Run Services**
    See [commands.md](file:///d:/Projects/blueprint-studio-ai/commands.md) to run the frontend server, backend API, and Celery worker concurrently.

---

## 📖 Additional Documentation

To make this repository fully self-contained and portfolio-ready, the following comprehensive guides have been created:
*   [commands.md](file:///d:/Projects/blueprint-studio-ai/commands.md) — Exact terminal commands for running all servers.
*   [install.md](file:///d:/Projects/blueprint-studio-ai/install.md) — Step-by-step setup guides, package files, and database schemas.
*   [theory.md](file:///d:/Projects/blueprint-studio-ai/theory.md) — Mathematical and logical background of latent diffusion, edge conditioning, SSIM, and semantic metrics.
*   [architecture.md](file:///d:/Projects/blueprint-studio-ai/architecture.md) — System flow charts, database ER diagrams, API routes, and websocket states.
