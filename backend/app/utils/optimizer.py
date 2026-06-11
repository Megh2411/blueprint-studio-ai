import os
import httpx

async def optimize_prompt(user_prompt: str) -> str:
    """
    Bypasses the unstable Google GenAI SDK entirely.
    Uses pure async HTTP REST calls to prevent Garbage Collection crashes
    and ASGI event loop conflicts.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found.")
        return user_prompt

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
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
            for attempt in range(3):
                try:
                    response = await client.post(url, json=payload, timeout=10.0)
                    if response.status_code in (429, 503, 502):
                        print(f"[WARN] Gemini async returned {response.status_code}. Retrying in {1.5 * (attempt + 1)}s...")
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    response.raise_for_status()
                    data = response.json()
                    break
                except Exception as attempt_err:
                    if attempt == 2:
                        raise attempt_err
                    print(f"[WARN] Gemini async attempt {attempt+1} failed: {attempt_err}. Retrying...")
                    await asyncio.sleep(1.5 * (attempt + 1))

            if not data:
                raise RuntimeError("Gemini failed to return data after async retries")

            # Parse the Gemini REST response structure
            optimized_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return optimized_text.strip()
            
    except Exception as e:
        print(f"REST API optimization failed, defaulting to original: {e}")
        return user_prompt