# Theoretical Foundations & Background 🧠🔬

This document provides a deep dive into the engineering principles, machine learning concepts, and mathematical metrics that power **Blueprint Studio AI**.

---

## 🎨 1. Latent Diffusion Models (LDMs)

Image generation in Blueprint Studio AI is based on **Latent Diffusion Models**. Traditional diffusion models apply noise to pixels in a high-dimensional space and learn to reverse the process. This is extremely computationally expensive.

Latent Diffusion Models solve this by operating in a lower-dimensional **latent space**.
1.  **Variational Autoencoder (VAE)**: Encodes a high-dimensional image $x$ into a compact latent representation $z = \mathcal{E}(x)$, and decodes it back to pixel space $x' = \mathcal{D}(z)$.
2.  **Forward Diffusion**: Adds Gaussian noise step-by-step to the latent representation $z$, resulting in a noisy latent $z_t$.
3.  **Denoising U-Net**: A neural network trained to predict the noise added at time step $t$, conditioned on text prompts (via CLIP text encoders) and structural vectors.
4.  **Reverse Diffusion**: Starting from random noise $z_T$, the U-Net iteratively subtracts the predicted noise, producing a clean latent $z_0$ that the VAE decodes into the final render.

---

## 📐 2. Structural Edge Conditioning (Image-to-Image & ControlNet)

To ensure the generated render matches the user's sketch or design composition, the pipeline utilizes **Structure Conditioning**.

In professional pipelines, **ControlNet** copies the weights of the U-Net's encoding blocks, keeping the original network locked. It takes an edge-condition map (like Canny, HED, Scribbles, or depth maps) and injects spatial boundaries directly into the U-Net's skip connections.

### Our Gemini 3.1 Flash-Lite + FLUX.1 Composition Pipeline
To bypass API restrictions on Hugging Face's serverless pipelines, Blueprint Studio AI implements a hybrid agentic architecture:
*   **Composition Mapping**: Instead of feeding pure noise, we use **Image-to-Image (Img2Img) Latent Initialization**. The U-Net is seeded with the structural canvas sketch directly (latents initialized from $\mathcal{E}(\text{sketch})$ instead of pure random noise).
*   **The Denoising Strength Hyperparameter ($S$)**: 
    *   If $S = 0.0$, the model outputs the original sketch exactly.
    *   If $S = 1.0$, the model ignores the sketch entirely and generates a completely random image from the prompt.
    *   At the default $S = 0.7$, the model has $30\%$ structural guidance (preserving lines, windows, and boundaries) and $70\%$ creative freedom to draw photorealistic textures, shadows, and materials.

---

## ⏱️ 3. Asynchronous Task Queuing (Celery + Redis)

Generating high-resolution AI renders takes anywhere from $5$ to $25$ seconds. Blocking the main HTTP connection while a model runs would lead to timeouts and a degraded user experience.

Blueprint Studio AI implements an **Asynchronous Task Pattern**:
1.  **Web Request Handlers**: The FastAPI router accepts the payload, inserts a `pending` job row into PostgreSQL, and schedules a Celery task.
2.  **Broker (Redis)**: Redis acts as the message broker, queuing incoming rendering tasks.
3.  **Background Worker (Celery)**: Background threads pick up the task from Redis, invoke the Hugging Face/Gemini APIs, calculate metrics, update PostgreSQL, and upload the image.
4.  **WebSocket Sync**: Upon completion, the worker notifies the client session over a WebSocket connection, triggering the frontend gallery to update in real-time.

---

## 📈 4. Real-time Telemetry Metrics

To provide objective evaluations of each run, Blueprint Studio AI calculates two telemetry metrics on the fly.

### A. Structural Similarity Index (SSIM)
SSIM compares structural composition between the input sketch and the output render. Unlike pixel-to-pixel Mean Squared Error (MSE), SSIM models human visual perception by comparing luminance, contrast, and structure.

For two images $x$ and $y$:

$$\text{SSIM}(x,y) = \frac{(2\mu_x\mu_y + C_1)(2\sigma_{xy} + C_2)}{(\mu_x^2 + \mu_y^2 + C_1)(\sigma_x^2 + \sigma_y^2 + C_2)}$$

Where:
*   $\mu_x, \mu_y$ are the average pixel intensities.
*   $\sigma_x^2, \sigma_y^2$ are the variances of $x$ and $y$.
*   $\sigma_{xy}$ is the covariance of $x$ and $y$.
*   $C_1 = (K_1 L)^2$ and $C_2 = (K_2 L)^2$ are constants to stabilize the division ($L$ is the dynamic range of pixel values, typically $255$).

### B. Semantic Score (CLIP Alignment via Gemini Vision)
CLIP (Contrastive Language-Image Pre-training) measures how closely an image matches a text description.

In this project, we implement a state-of-the-art **LLM-as-an-Evaluator** pattern. The generated image along with the generation prompt is sent to **Gemini 3.1 Flash-Lite**. The model evaluates the semantic composition of the image (e.g. materials, spatial alignment, atmospheric lighting) against the requested description, returning a standardized mathematical score between $0.000$ and $1.000$.

---

## 🔑 5. API Key Pooling & Failover Rotation

Free-tier public APIs (like Google Gemini and Hugging Face Serverless) enforce strict rate limits:
*   **Gemini 3.1 Flash-Lite**: Capped at 15 Requests Per Minute (RPM) and 500 Requests Per Day (RPD) on the free tier.
*   **Hugging Face**: Capped by total request credits or concurrency constraints (often returning HTTP `429 Too Many Requests` or `402 Payment Required`).

To ensure high availability and prevent application-level failures, Blueprint Studio AI implements an **API Key Rotation Pool**:
1.  **Environment Pools**: API keys are loaded as a comma-separated list: `API_KEYS = [k.strip() for k in os.getenv("API_KEY").split(",") if k.strip()]`.
2.  **Sequential Failover**: The API client makes a request using `API_KEYS[0]`.
3.  **Dynamic Exception Interception**: If the request fails with a status code of `429`, `402`, `403`, or `503`, the client intercepts the exception, rotates to the next index `API_KEYS[1]`, sleeps for a short duration (exponential backoff), and attempts the operation again.
4.  **Resilience**: The pipeline will only raise a user-facing error if *all* keys in the configured pool fail.

---

## 🛡️ 6. Redis-Backed Rate Limiting Security

To protect our third-party API quotas from malicious abuse or infinite loops, the FastAPI backend applies a **Fixed-Window Rate Limiting** algorithm implemented over our **Upstash Redis** instance.

### The Algorithm
For each client request to a protected endpoint:
1.  Identify the client identifier (host IP address $IP$ and route path $Route$).
2.  Construct a unique Redis key: $Key = \text{"rate\_limit:"} + IP + \text{":"} + Route$.
3.  Query the key's current value in Redis:
    *   If the key does not exist: Initialize the key to $1$ and set a Time-To-Live (TTL) expiry of $60$ seconds.
    *   If the key exists and its value is less than the limit $N$: Increment the value by $1$.
    *   If the key exists and its value is greater than or equal to $N$: Reject the request instantly, returning an HTTP `429 Too Many Requests` status code along with the remaining TTL value as `Retry-After`.
4.  **Soft-Fail Safety**: In the event of a Redis connection loss, the middleware catches the connection error and allows the request to proceed (failing soft), ensuring that rate-limiter infrastructure downtime never disrupts end-user accessibility.

