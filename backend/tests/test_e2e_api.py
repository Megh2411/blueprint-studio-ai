import os
import base64
import requests
import time
import uuid
from PIL import Image, ImageDraw
import io

# 1. Create a red rose test image programmatically
img = Image.new("RGB", (256, 256), color="red")
draw = ImageDraw.Draw(img)
draw.ellipse([50, 50, 200, 200], fill="red", outline="darkred", width=3)
draw.line([128, 200, 128, 250], fill="green", width=5)
draw.polygon([128, 220, 100, 210, 128, 230], fill="green")

# Base64 encode
buffered = io.BytesIO()
img.save(buffered, format="PNG")
img_b64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")

client_id = str(uuid.uuid4())
print(f"Test Client ID: {client_id}")

# 2. Call create job passing hyperparameters
url = "http://127.0.0.1:8000/api/renders"
payload = {
    "user_id": client_id,
    "prompt": "create a hibiscus similar to the image",
    "sketch_base64": img_b64,
    "mode": "sketch",
    "control_strength": 0.8,
    "steps": 20,
    "cfg_scale": 8.0
}

print("\n1. Sending POST request to create render job...")
try:
    r = requests.post(url, json=payload, timeout=20)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    r.raise_for_status()
    job_id = r.json()["job_id"]
    print(f"Job successfully created! Job ID: {job_id}")

    # 3. Poll for status
    print("\n2. Polling for job completion...")
    completed = False
    for i in range(25):
        time.sleep(3)
        status_r = requests.get(f"{url}/{job_id}")
        status_r.raise_for_status()
        job = status_r.json()
        print(f"Poll {i+1}: Status = {job['status']}")
        if job["status"] == "completed":
            print(f"Job completed! Output URL: {job['render_path']}")
            completed = True
            break
        elif job["status"] == "failed":
            print(f"Job failed! Error log: {job.get('error_log')}")
            break

    if completed:
        print("\n3. Testing history endpoint...")
        history_r = requests.get(f"{url}/history/{client_id}")
        history_r.raise_for_status()
        history = history_r.json()
        print(f"History returned {len(history)} items:")
        for h in history:
            print(f"- Job: {h['job_id']}, Prompt: '{h['prompt']}', Render Path: {h['render_path']}")
    else:
        print("\nJob did not complete successfully.")

except Exception as e:
    print(f"Test failed: {e}")
