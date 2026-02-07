import os
import json
import yaml
import time
import requests
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import fal_client
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# טעינת הגדרות
with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)
with open(config["paths"]["assets"], "r", encoding="utf-8") as f: assets = yaml.safe_load(f)

# יצירת תיקיית פלט מסודרת + תיקייה שטוחה לנוחות
FLAT_DIR = "production/flat_images"
os.makedirs(config["paths"]["images_output"], exist_ok=True)
os.makedirs(FLAT_DIR, exist_ok=True)

FLUX_MODEL = config["models"]["flux"]

# --- פונקציית LoRA ---
def get_lora_config():
    lora_source = assets.get("lora_url")
    if not lora_source: return None
    if os.path.exists(lora_source):
        print(f"📤 Uploading local LoRA: {lora_source}...")
        try:
            uploaded_url = fal_client.upload_file(lora_source)
            return {"path": uploaded_url, "scale": 1.0}
        except Exception as e:
            print(f"⚠️ Failed to upload LoRA: {e}")
            return None
    return {"path": lora_source, "scale": 1.0}

GLOBAL_LORA_CONFIG = get_lora_config()

def parse_shot_range(user_input):
    target_ids = []
    user_input = user_input.strip().upper()
    if "-" in user_input:
        try:
            start_str, end_str = user_input.split("-")
            start_num = int(re.search(r'\d+', start_str).group())
            end_num = int(re.search(r'\d+', end_str).group())
            for i in range(start_num, end_num + 1):
                target_ids.append(f"SHOT_{i:03d}")
        except: return []
    else:
        try:
            num = int(re.search(r'\d+', user_input).group())
            target_ids.append(f"SHOT_{num:03d}")
        except: target_ids.append(user_input)
    return target_ids

@retry(wait=wait_exponential(multiplier=1, min=4, max=60), stop=stop_after_attempt(5), reraise=True)
def generate_image_task(shot_id, prompt):
    print(f"🎨 {shot_id}: Sending to Flux...")
    
    args = {
        "prompt": prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": config["pipeline"].get("flux_steps", 28),
        "guidance_scale": 3.5,
        "enable_safety_checker": False,
        "output_format": "jpeg"
    }
    
    if GLOBAL_LORA_CONFIG:
        args["loras"] = [GLOBAL_LORA_CONFIG]

    result = fal_client.submit(FLUX_MODEL, arguments=args).get()
    image_url = result["images"][0]["url"]
    
    response = requests.get(image_url)
    if response.status_code == 200:
        filename = f"{shot_id}.jpg"
        
        # 1. שמירה בתיקייה המקורית
        save_path = os.path.join(config["paths"]["images_output"], filename)
        with open(save_path, "wb") as f:
            f.write(response.content)
            
        # 2. שמירה בתיקייה השטוחה (לנוחות)
        flat_path = os.path.join(FLAT_DIR, filename)
        shutil.copy(save_path, flat_path)
        
        return {"id": shot_id, "status": "SUCCESS", "path": save_path, "flat_path": flat_path}
    else:
        raise Exception(f"Failed to download image from {image_url}")

def process_shot(shot_id):
    shot = shots.get(shot_id)
    if not shot: return {"id": shot_id, "status": "SKIPPED", "msg": "Not found"}
    
    # --- התיקון: ביטול בדיקת ה-SKIPPED ---
    # הבלוק הזה אחראי לדילוג. שמתי אותו בהערה כדי שידרוס תמיד.
    # if os.path.exists(os.path.join(config["paths"]["images_output"], f"{shot_id}.jpg")):
    #    return {"id": shot_id, "status": "SKIPPED", "msg": "Image exists"}
    # -------------------------------------

    prompt_path = shot["stills"]["prompt_file"]
    if not os.path.exists(prompt_path): return None
    
    with open(prompt_path, "r", encoding="utf-8") as f: prompt = f.read()

    try:
        return generate_image_task(shot_id, prompt)
    except Exception as e:
        return {"id": shot_id, "status": "ERROR", "msg": str(e)}

def main():
    print("--- Flux Image Generator (FORCE REGENERATE MODE) ---")
    if GLOBAL_LORA_CONFIG: print(f"🦄 LoRA Active")
    
    user_input = input("Enter Range (e.g., 1-5), or ENTER for ALL: ").strip()
    
    target_shots = []
    if not user_input:
        # לוקח רק את מה שמאושר
        target_shots = [sid for sid, data in shots.items() if data["stills"]["status"] == "APPROVED"]
    else:
        requested_ids = parse_shot_range(user_input)
        # לוקח את הטווח המבוקש, בתנאי שהוא מאושר
        target_shots = [sid for sid in requested_ids if sid in shots and shots[sid]["stills"]["status"] == "APPROVED"]

    if not target_shots:
        print("🤷 No approved shots found to generate.")
        return

    print(f"🚀 Starting Flux Generation for {len(target_shots)} shots (Overwriting old images)...")
    
    MAX_CONCURRENCY = 5 
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
        future_to_shot = {executor.submit(process_shot, sid): sid for sid in target_shots}
        
        for future in as_completed(future_to_shot):
            res = future.result()
            if res:
                if res["status"] == "SUCCESS":
                    print(f"✅ {res['id']}: OVERWRITTEN -> {res['flat_path']}")
                    shots[res['id']]["stills"]["image_path"] = res["path"]
                    shots[res['id']]["stills"]["status"] = "IMAGE_READY"
                elif res["status"] == "ERROR":
                    print(f"❌ {res['id']}: Failed - {res['msg']}")

    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)
    
    print(f"\n📁 New images are waiting in: {FLAT_DIR}")

if __name__ == "__main__":
    main()