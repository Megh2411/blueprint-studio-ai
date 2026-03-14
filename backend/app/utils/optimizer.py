import os
import httpx

async def optimize_prompt(user_prompt: str) -> str:
    """
    Bypasses the unstable Google GenAI SDK entirely.
    Uses pure async HTTP REST calls to prevent Garbage Collection crashes
    and ASGI event loop conflicts.
    """
    raw_keys = os.getenv("GEMINI_API_KEY", "")
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
    if not api_keys:
        print("Warning: GEMINI_API_KEY not found.")
        return user_prompt

    system_instruction = (
        "You are an expert prompt engineer for generative AI models. "
        "Your task is to take a short, simple prompt describing an object, scene, space, or building and expand it "
        "into a highly detailed, professional prompt for Stable Diffusion or FLUX. "
        "If the prompt describes a building, interior, or architectural space, optimize it for architecture (include specific styles, materials like exposed concrete or timber, and volumetric lighting). "
        "If the prompt describes a general object, flower, animal, or scene (e.g., 'a hibiscus' or 'cute dolphin'), optimize it for high-quality product design, realistic photography, or digital art (include texture details, studio lighting, depth of field, and styling). "
        "Be concise (under 80 words). Ensure your output is a complete, fully finished sentence or description, and never cut off mid-sentence. "
        "Avoid conversational filler; return ONLY the final optimized prompt."
    )

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {"parts": [{"text": f"Expand this prompt: {user_prompt}"}]}
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2000
        }
    }

    try:
        # Use httpx for a pure, native async network call
        import asyncio
        async with httpx.AsyncClient() as client:
            data = None
            for key_idx, api_key in enumerate(api_keys):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
                for attempt in range(2):
                    try:
                        response = await client.post(url, json=payload, timeout=10.0)
                        if response.status_code in (429, 503, 502):
                            print(f"[WARN] Gemini key {key_idx+1} returned {response.status_code}. Trying next key...")
                            await asyncio.sleep(1.0)
                            break # Break inner loop to try the next key
                        response.raise_for_status()
                        data = response.json()
                        break
                    except Exception as attempt_err:
                        if attempt == 1 and key_idx == len(api_keys) - 1:
                            raise attempt_err
                        print(f"[WARN] Gemini key {key_idx+1} attempt {attempt+1} failed: {attempt_err}. Retrying...")
                        await asyncio.sleep(1.0)
                
                if data:
                    break

            if not data:
                raise RuntimeError("All Gemini keys in the pool failed to return data")

            # Parse the Gemini REST response structure
            optimized_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return optimized_text.strip()
            
    except Exception as e:
        print(f"REST API optimization failed, defaulting to original: {e}")
        return user_prompt