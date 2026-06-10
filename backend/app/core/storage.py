import base64
import uuid
from supabase import create_client, Client
from app.core.config import settings

# Initialize the official Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

def upload_sketch(base64_string: str) -> str:
    """
    Decodes a Base64 image and uploads it to the Supabase 'sketches' bucket.
    Returns the public URL of the uploaded image.
    """
    # 1. Clean the string. React often sends "data:image/png;base64,iVBORw0KGgo..."
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
        
    # 2. Decode the string into raw image bytes
    image_bytes = base64.b64decode(base64_string)
    
    # 3. Generate a unique filename
    file_name = f"{uuid.uuid4()}.png"
    
    # 4. Upload to the 'sketches' bucket
    supabase.storage.from_("sketches").upload(
        path=file_name,
        file=image_bytes,
        file_options={"content-type": "image/png"}
    )
    
    # 5. Get and return the public URL
    return supabase.storage.from_("sketches").get_public_url(file_name)
def upload_render(image_bytes: bytes) -> str:
    """
    Uploads the final generated AI image bytes to the Supabase 'renders' bucket.
    """
    file_name = f"final_{uuid.uuid4()}.png"
    
    supabase.storage.from_("renders").upload(
        path=file_name,
        file=image_bytes,
        file_options={"content-type": "image/png"}
    )
    
    return supabase.storage.from_("renders").get_public_url(file_name)