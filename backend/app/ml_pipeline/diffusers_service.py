import os
import io
import base64
import requests
from PIL import Image
from typing import Any

class GeneratedImageResult:
    """Result class to match image generation pipeline output structure."""
    def __init__(self, image: Image.Image):
        self.images = [image]

class StableDiffusionImageToImageService:
    """
    Production-ready sketch-to-render and text-to-image service.
    Utilizes a Google Gemini + Hugging Face FLUX.1 layout-preserving pipeline.
    """

    def __init__(self, model_id: str = "black-forest-labs/FLUX.1-schnell") -> None:
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
        Generates an image using Gemini Layout Mapping and FLUX.1.
        """
        from app.core.config import settings
        raw_keys = settings.GEMINI_API_KEY or ""
        api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        hf_key = settings.HUGGINGFACE_API_KEY
 
        if not api_keys or not hf_key:
            raise ValueError("Both GEMINI_API_KEY and HUGGINGFACE_API_KEY must be set in backend .env.")
 
        import numpy as np
        img_np = np.array(image.convert("L"))
        # The canvas default background is filled with solid white (pixel value 255)
        # If the mean is greater than 254.0, the canvas is blank/empty (no sketch drawn)
        is_blank_canvas = float(img_np.mean()) > 254.0
        
        if is_blank_canvas:
            print("[ML] Canvas is blank/untouched. Skipping Gemini layout mapper and doing pure Txt2Img...")
            refined_prompt = prompt
        else:
            print("[ML] Running Gemini + FLUX Hybrid layout mapper...")
            # Base64 encode the sketch
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            image_b64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
            
            # Use Gemini to describe composition and preserve structure
            system_instruction = (
                "You are an AI layout-preserving prompt architect. Your job is to analyze the user's sketch and text prompt, and write a single, cohesive, highly descriptive prompt for an image generator. "
                "Describe the subject, colors, composition, and background, ensuring you match the shapes and positions from the sketch. "
                "Be extremely concise (under 60 words). Return ONLY the final prompt. Do not include any intro, conversational filler, markdown, or incomplete sentences."
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
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2000
                }
            }
            
            try:
                # Robust retry logic with key rotation pooling (handling 429/503 rate limits)
                import time
                data = None
                for key_idx, api_key in enumerate(api_keys):
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                    for attempt in range(2):
                        try:
                            gemini_r = requests.post(gemini_url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                            if gemini_r.status_code in (429, 503, 502):
                                print(f"[WARN] Gemini key {key_idx+1} returned {gemini_r.status_code}. Trying next key...")
                                time.sleep(1.0)
                                break # Break inner loop to try next key in the pool
                            gemini_r.raise_for_status()
                            data = gemini_r.json()
                            break
                        except Exception as attempt_err:
                            if attempt == 1 and key_idx == len(api_keys) - 1:
                                raise attempt_err
                            print(f"[WARN] Gemini key {key_idx+1} attempt {attempt+1} failed: {attempt_err}. Retrying...")
                            time.sleep(1.0)
                    
                    if data:
                        break
                
                if not data:
                    raise RuntimeError("All Gemini keys in the pool failed to return data after retries")

                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        refined_prompt = parts[0].get("text", "").strip()
                        print(f"[ML] Gemini Layout Prompt Map: {refined_prompt}")
                    else:
                        raise KeyError("parts")
                else:
                    raise KeyError("candidates")
            except Exception as err:
                print(f"[WARN] Gemini layout mapper failed: {err}. Falling back to original prompt.")
                refined_prompt = prompt
        
        # Define URLs to try in case of DNS/network resolution issues
        hf_urls = [
            f"https://api-inference.huggingface.co/models/{self.model_id}",
            f"https://router.huggingface.co/hf-inference/models/{self.model_id}"
        ]
        
        last_error = None
        for hf_url in hf_urls:
            import time
            for attempt in range(2):
                try:
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
                    last_error = err
                    print(f"[ML] Attempt {attempt+1} failed for {hf_url}: {err}")
                    time.sleep(1.5)
        
        raise RuntimeError(f"Model generation failed: {last_error}")
