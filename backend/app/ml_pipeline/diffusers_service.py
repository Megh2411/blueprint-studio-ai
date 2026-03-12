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
        Generates an image using Gemini Layout Mapping and FLUX.1.
        """
        from app.core.config import settings
        gemini_key = settings.GEMINI_API_KEY
        hf_key = settings.HUGGINGFACE_API_KEY

        if not gemini_key or not hf_key:
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
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            system_instruction = (
                "You are an AI layout-preserving prompt architect. Your job is to analyze the user's input image (which might be a crude sketch or a drawing) "
                "and their text prompt. Describe the composition, geometry, visual structure, shapes, and positions of items in the image, "
                "and rewrite the description to match the user's target prompt. For example, if the image shows a red rose in the center with a green stem "
                "and the user prompt is 'create a hibiscus similar to the image', output a detailed prompt for a text-to-image model describing a "
                "hibiscus flower located in the exact same center position, with similar stem structure and background composition. "
                "Be concise (under 80 words). Ensure your output is a complete, fully finished sentence or description, and never cut off mid-sentence. "
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
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 300
                }
            }
            
            try:
                gemini_r = requests.post(gemini_url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                gemini_r.raise_for_status()
                data = gemini_r.json()
                
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
        
        try:
            # Use official, stable Hugging Face Inference API
            hf_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
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
            raise RuntimeError(f"Model generation failed: {err}")
