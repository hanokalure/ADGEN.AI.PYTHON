import os
import base64
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = FastAPI(title="AdGen.AI")

# Hugging Face Configuration
HF_INFERENCE_BASE = os.getenv("HF_INFERENCE_BASE", "https://router.huggingface.co/hf-inference")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")

def get_hf_token() -> str:
    token = os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_API_KEY") or ""
    return token.strip().strip('"').strip("'")

def get_gemini_token() -> str:
    token = os.getenv("GEMINI_API_KEY") or ""
    return token.strip().strip('"').strip("'")

def dimensions_for_aspect_ratio(aspect_ratio: Optional[str]):
    if aspect_ratio == "16:9":
        return 1024, 576
    elif aspect_ratio == "9:16":
        return 576, 1024
    elif aspect_ratio == "4:3":
        return 1024, 768
    else: # 1:1 default
        return 1024, 1024

def build_final_enhanced_prompt(gemini_prompt: str) -> str:
    base = gemini_prompt.strip()
    return (
        f"{base},\n\n"
        "ultra realistic, 4k, highly detailed, professional product photography, "
        "studio lighting, sharp focus, clean composition, "
        "commercial advertising style, premium branding, "
        "cinematic lighting, depth of field, no text, no watermark"
    )

class AdGenerationRequest(BaseModel):
    productName: str
    targetAudience: Optional[str] = ""
    adGoal: str
    adStyle: Optional[str] = "Photorealistic"
    aspectRatio: Optional[str] = "16:9"

@app.post("/api/generate")
async def generate_ad(req: AdGenerationRequest):
    if not req.productName or not req.adGoal:
        raise HTTPException(status_code=400, detail="Product name and ad goal are required.")

    hf_token = get_hf_token()
    if not hf_token:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: set HF_API_KEY (or HUGGINGFACE_API_KEY) in environment variables."
        )

    gemini_key = get_gemini_token()
    if not gemini_key:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: set GEMINI_API_KEY in environment variables."
        )

    # 1. Enhance prompt using Gemini
    system_instruction = """
You are a professional advertising creative director.

Generate a highly detailed image prompt for a product advertisement.

Include:
- product appearance
- scene composition
- lighting style
- camera angle
- mood

Make it visually rich and cinematic.

STRICT:
- no text
- no logos
- no explanation
- output only the prompt
"""
    user_prompt = f"""
Product: {req.productName}
Audience: {req.targetAudience or 'General audience'}
Goal: {req.adGoal}
Style: {req.adStyle}
"""

    try:
        client = genai.Client(api_key=gemini_key)
        # We try gemini-2.5-flash or gemini-1.5-flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config={
                "system_instruction": system_instruction
            }
        )
        gemini_prompt = response.text.strip() if response.text else None
    except Exception as e:
        # Fallback to direct HTTP or gemini-1.5-flash if gemini-2.5-flash is not found
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=user_prompt,
                config={
                    "system_instruction": system_instruction
                }
            )
            gemini_prompt = response.text.strip() if response.text else None
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Gemini prompt generation failed: {str(err)}")

    if not gemini_prompt:
        raise HTTPException(status_code=500, detail="No prompt was returned from Gemini.")

    final_enhanced_prompt = build_final_enhanced_prompt(gemini_prompt)
    width, height = dimensions_for_aspect_ratio(req.aspectRatio)

    parameters = {"width": width, "height": height}
    if "FLUX.1-schnell" in HF_IMAGE_MODEL:
        parameters["num_inference_steps"] = 4

    hf_url = f"{HF_INFERENCE_BASE}/models/{HF_IMAGE_MODEL}"
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": final_enhanced_prompt,
        "parameters": parameters,
        "options": {"wait_for_model": True}
    }

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        hf_response = await http_client.post(hf_url, headers=headers, json=payload)
        
        content_type = hf_response.headers.get("content-type", "")

        if hf_response.status_code != 200:
            detail = hf_response.reason_phrase
            if "application/json" in content_type:
                try:
                    err_json = hf_response.json()
                    if isinstance(err_json, dict) and "error" in err_json:
                        detail = str(err_json["error"])
                    else:
                        detail = str(err_json)
                except Exception:
                    pass
            raise HTTPException(
                status_code=hf_response.status_code,
                detail=f"Hugging Face image generation failed ({hf_response.status_code}): {detail}"
            )

        if not content_type.startswith("image/"):
            text_snippet = hf_response.text[:200]
            raise HTTPException(
                status_code=500,
                detail=f"Hugging Face returned non-image response: {text_snippet}"
            )

        image_base64 = base64.b64encode(hf_response.content).decode("utf-8")

    return {
        "image": image_base64,
        "enhancedPrompt": final_enhanced_prompt
    }

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def serve_root():
    return FileResponse(os.path.join(static_dir, "index.html"))
