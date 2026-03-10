import os
import io
import time
import base64
import requests
from PIL import Image
from typing import Any

class GeneratedImageResult:
    """Mock result class to match diffusers API output structure."""
    def __init__(self, image: Image.Image):
        self.images = [image]

class StableDiffusionImageToImageService:
    """
    Production-ready image-to-image and sketch-to-render service.
    Supports Replicate, Stability AI, and a free Gemini + FLUX hybrid pipeline.
    """

    def __init__(self, model_id: str = "runwayml/stable-diffusion-v1-5") -> None:
        self.model_id = model_id

    def generate(
        self, 
        prompt: str, 
        image: Image.Image, 
        image_url: str = None, 
        strength: float = 0.65, 
        guidance_scale: float = 7.5,
        num_inference_steps: int = 25,
        **kwargs: Any
    ) -> GeneratedImageResult:
        """
        Generates an image-to-image render routing through available environment configurations.
        """
        from app.core.config import settings
        replicate_token = settings.REPLICATE_API_TOKEN
        stability_key = settings.STABILITY_API_KEY
        gemini_key = settings.GEMINI_API_KEY
        hf_key = settings.HUGGINGFACE_API_KEY

        # 1. Option A: Replicate (ControlNet/SDXL img2img)
        if replicate_token:
            print("[ML] Using Replicate API...")
            try:
                # If no public URL is provided, upload the PIL image to Supabase Storage first
                if not image_url:
                    from app.core.storage import upload_render
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    image_url = upload_render(img_byte_arr.getvalue())
                    print(f"Uploaded temp sketch to storage for Replicate: {image_url}")

                headers = {
                    "Authorization": f"Token {replicate_token}",
                    "Content-Type": "application/json"
                }
                
                # SDXL img2img version
                payload = {
                    "version": "39ed7e9d4c109033d0fd66a65513ca1ad5ab2e2d55a354b868d1826201a9617a",
                    "input": {
                        "prompt": prompt,
                        "image": image_url,
                        "prompt_strength": max(0.0, min(1.0, 1.0 - strength)),
                        "guidance_scale": guidance_scale,
                        "num_inference_steps": num_inference_steps
                    }
                }
                
                r = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload, timeout=20)
                r.raise_for_status()
                pred = r.json()
                poll_url = pred["urls"]["get"]

                for _ in range(60):
                    time.sleep(1.5)
                    poll_r = requests.get(poll_url, headers=headers, timeout=10)
                    poll_r.raise_for_status()
                    poll_data = poll_r.json()
                    if poll_data["status"] == "succeeded":
                        out_url = poll_data["output"][0]
                        img_r = requests.get(out_url, timeout=15)
                        img_r.raise_for_status()
                        res_img = Image.open(io.BytesIO(img_r.content)).convert("RGB")
                        return GeneratedImageResult(res_img)
                    elif poll_data["status"] == "failed":
                        raise Exception(f"Replicate error: {poll_data.get('error')}")

                raise TimeoutError("Replicate generation timed out.")
            except Exception as err:
                print(f"[WARN] Replicate failed: {err}. Falling back to Gemini+FLUX hybrid...")

        # 2. Option B: Stability AI Image-to-Image API
        if stability_key and stability_key != "not_needed_anymore":
            print("[ML] Using Stability AI API...")
            try:
                url = "https://api.stability.ai/v2beta/stable-image/generate/image-to-image"
                headers = {
                    "Authorization": f"Bearer {stability_key}",
                    "Accept": "image/*"
                }
                
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                
                files = {
                    "image": ("image.png", img_byte_arr.getvalue(), "image/png")
                }
                data = {
                    "prompt": prompt,
                    "output_format": "png",
                    "strength": strength # Typically 0.0 to 1.0
                }
                
                r = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                if r.status_code == 200:
                    res_img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    return GeneratedImageResult(res_img)
                else:
                    raise Exception(f"Stability error: {r.text}")
            except Exception as err:
                print(f"[WARN] Stability AI failed: {err}. Falling back to Gemini+FLUX hybrid...")

        # 3. Option C: Gemini + FLUX Hybrid Layout-Preserving Pipeline (Zero-Cost Fallback)
        if gemini_key and hf_key:
            print("[ML] Running Gemini + FLUX Hybrid layout mapper...")
            
            # Base64 encode the sketch
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            image_b64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
            
            # Use Gemini to describe composition and preserve structure
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            system_instruction = (
                "You are an AI layout-preserving prompt architect. Your job is to analyze the user's input image (which might be a crude sketch or a drawing) "
                "and their text prompt. Describe the composition, geometry, visual structure, shapes, and positions of items in the image, "
                "and rewrite the description to match the user's target prompt. For example, if the image shows a red rose in the center with a green stem "
                "and the user prompt is 'create a hibiscus similar to the image', output a detailed prompt for a text-to-image model describing a "
                "hibiscus flower located in the exact same center position, with similar stem structure and background composition. "
                "Return ONLY the final detailed prompt. Do not include any intro, markdown, or chat text."
            )
            
            payload = {
                "system_instruction": {
                    "parts": [{"text": system_instruction}]
                },
                "contents": [
                    {
                        "parts": [
                            {"inlineData": {"mimeType": "image/png", "data": image_b64}},
                            {"text": f"User target prompt: {prompt}"}
                        ]
                    }
                ]
            }
            
            try:
                gemini_r = requests.post(gemini_url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                gemini_r.raise_for_status()
                refined_prompt = gemini_r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"[ML] Gemini Layout Prompt Map: {refined_prompt}")
                
                # Call FLUX.1-schnell on Hugging Face Serverless API
                hf_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
                hf_headers = {
                    "Authorization": f"Bearer {hf_key}",
                    "Content-Type": "application/json"
                }
                flux_payload = {
                    "inputs": refined_prompt
                }
                
                flux_r = requests.post(hf_url, headers=hf_headers, json=flux_payload, timeout=25)
                flux_r.raise_for_status()
                
                res_img = Image.open(io.BytesIO(flux_r.content)).convert("RGB")
                return GeneratedImageResult(res_img)
            except Exception as err:
                raise RuntimeError(f"Hybrid pipeline failed: {err}")
                
        raise ValueError("No valid API credentials (Replicate, Stability, or Gemini+HF keys) found in environment.")
