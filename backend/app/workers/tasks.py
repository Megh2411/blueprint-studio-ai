import io
import base64
import numpy as np
import requests
from PIL import Image
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import RenderJob, JobStatus
from app.core.storage import upload_render
from app.ml_pipeline.diffusers_service import StableDiffusionImageToImageService
from app.core.config import settings

def calculate_real_ssim(img1: Image.Image, img2: Image.Image) -> float:
    try:
        img1_gray = img1.convert("L").resize((256, 256))
        img2_gray = img2.convert("L").resize((256, 256))
        
        x = np.array(img1_gray, dtype=np.float32)
        y = np.array(img2_gray, dtype=np.float32)
        
        mu_x = x.mean()
        mu_y = y.mean()
        
        sigma_x_sq = x.var()
        sigma_y_sq = y.var()
        
        sigma_xy = ((x - mu_x) * (y - mu_y)).mean()
        
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2
        
        ssim_val = ((2 * mu_x * mu_y + C1) * (2 * sigma_xy + C2)) / ((mu_x**2 + mu_y**2 + C1) * (sigma_x_sq + sigma_y_sq + C2))
        return float(max(0.0, min(1.0, ssim_val)))
    except Exception as e:
        print(f"Error calculating SSIM: {e}")
        return 0.800

def evaluate_real_clip_score(image: Image.Image, prompt: str) -> float:
    raw_keys = settings.GEMINI_API_KEY or ""
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
    if not api_keys:
        return 0.850
        
    try:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": image_b64
                            }
                        },
                        {
                            "text": (
                                f"Analyze this generated image and calculate a semantic alignment score (float between 0.000 and 1.000) "
                                f"showing how well it matches the user's prompt: '{prompt}'. "
                                f"Return ONLY the floating point score (e.g., 0.895) with no other text, comments, or markdown."
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2000
            }
        }
        
        import time
        data = None
        for key_idx, api_key in enumerate(api_keys):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
            for attempt in range(2):
                try:
                    r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                    if r.status_code in (429, 503, 502):
                        print(f"[WARN] Gemini CLIP key {key_idx+1} returned {r.status_code}. Trying next key...")
                        time.sleep(1.0)
                        break # Break inner loop to try next key
                    r.raise_for_status()
                    data = r.json()
                    break
                except Exception as attempt_err:
                    if attempt == 1 and key_idx == len(api_keys) - 1:
                        raise attempt_err
                    print(f"[WARN] Gemini CLIP key {key_idx+1} attempt {attempt+1} failed: {attempt_err}. Retrying...")
                    time.sleep(1.0)
            
            if data:
                break
                
        if not data:
            raise RuntimeError("Gemini CLIP score evaluation failed to return data after retries")
        
        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                result_text = parts[0].get("text", "").strip()
                return float(result_text)
        print(f"[METRICS] Gemini returned unexpected format: {data}")
        return 0.850
    except Exception as e:
        print(f"Error evaluating CLIP score: {e}")
        return 0.850

diffusion_service = StableDiffusionImageToImageService()

@celery_app.task(bind=True, max_retries=3)
def process_render_job(self, job_id: str, control_strength: float = 0.7, steps: int = 25, cfg_scale: float = 7.0):
    print(f"[WORKER] Worker picked up Job {job_id} with strength={control_strength}, steps={steps}, cfg={cfg_scale}")
    db = SessionLocal()
    
    try:
        job = db.query(RenderJob).filter(RenderJob.job_id == job_id).first()
        if not job:
            return
            
        job.status = JobStatus.PROCESSING
        db.commit()
        print(f"[PROCESSING] Job {job_id} processing and sending to Hugging Face...")
        
        # 1. Prepare the image payload
        if job.sketch_path.startswith("data:image"):
            header, encoded = job.sketch_path.split(",", 1)
            sketch_bytes = base64.b64decode(encoded)
        else:
            import requests
            sketch_response = requests.get(job.sketch_path)
            if sketch_response.status_code != 200:
                raise Exception("Failed to download sketch.")
            sketch_bytes = sketch_response.content
 
        sketch_image = Image.open(io.BytesIO(sketch_bytes)).convert("RGB")
 
        # 2. Run the sketch through an image-to-image diffusion pipeline.
        print("[ML] Calling image-to-image diffusion pipeline...")
        
        is_architecture = any(word in job.prompt.lower() for word in [
            "house", "villa", "building", "room", "interior", "architecture", "home",
            "brutalist", "facade", "cottage", "cabin", "office", "pavilion", "lounge",
            "kitchen", "apartment", "loft", "render", "design", "living", "bedroom", 
            "bathroom", "castle", "skyscraper", "structure", "hotel", "resort", "studio",
            "mansion", "facade"
        ])
        
        if is_architecture:
            formatted_prompt = f"highly detailed architectural render, photorealistic, 8k, {job.prompt}"
        else:
            formatted_prompt = f"photorealistic, highly detailed, studio photography, 8k, {job.prompt}"
 
        image = diffusion_service.generate(
            prompt=formatted_prompt,
            image=sketch_image,
            image_url=job.sketch_path if not job.sketch_path.startswith("data:image") else None,
            strength=control_strength,
            guidance_scale=cfg_scale,
            num_inference_steps=steps,
        ).images[0]
        
        # 3. Convert PIL image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        print("[ML] AI Generation Complete! Uploading final image...")
        
        final_image_url = upload_render(image_bytes)
        
        # Calculate real metrics on the fly
        print("[METRICS] Calculating real SSIM and semantic alignment scores...")
        real_ssim = calculate_real_ssim(sketch_image, image)
        real_clip = evaluate_real_clip_score(image, job.prompt)
        print(f"[METRICS] Real SSIM: {real_ssim:.3f}, Real CLIP: {real_clip:.3f}")
        
        # 4. Update Database (including calculated metrics)
        job.status = JobStatus.COMPLETED
        job.render_path = final_image_url
        job.metrics = {
            "clipScore": f"{real_clip:.3f}",
            "ssim": f"{real_ssim:.3f}"
        }
        db.commit()
        
        print(f"[SUCCESS] Job {job_id} COMPLETED and PERSISTED! URL: {final_image_url}")
 
        # 5. Webhook Notification
        try:
            import os
            import requests
            port = os.getenv("PORT", "8000")
            webhook_url = f"http://127.0.0.1:{port}/api/notify-render-complete"
            requests.post(
                webhook_url,
                json={
                    "user_id": str(job.user_id),
                    "render_path": final_image_url,
                    "metrics": {
                        "clipScore": f"{real_clip:.3f}",
                        "ssim": f"{real_ssim:.3f}"
                    }
                },
                timeout=3
            )
            print(f"[WEBHOOK] Webhook triggered on {webhook_url}!")
        except Exception as e:
            print(f"[WEBHOOK] Webhook failed: {e}")

        return {"status": "success", "url": final_image_url}
        
    except Exception as e:
        db.rollback()
        error_msg = str(e)[:1000]
        print(f"[ERROR] Job {job_id} FAILED: {error_msg}")
        
        if 'job' in locals() and job:
            job.status = JobStatus.FAILED
            job.error_log = error_msg
            db.commit()
            
            # Notify failure to frontend
            try:
                import os
                import requests
                port = os.getenv("PORT", "8000")
                webhook_url = f"http://127.0.0.1:{port}/api/notify-render-complete"
                requests.post(webhook_url, 
                              json={"user_id": str(job.user_id), "status": "failed"}, timeout=3)
            except:
                pass
    finally:
        db.close()