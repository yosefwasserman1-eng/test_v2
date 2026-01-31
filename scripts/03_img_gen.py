import os
import json
import yaml
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import fal_client
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# טעינת סביבה
load_dotenv()

# טעינת הגדרות
with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

# יצירת תיקיית פלט
os.makedirs(config["paths"]["images_output"], exist_ok=True)

# הגדרות מודל FLUX
FLUX_MODEL = config["models"]["flux"]
LORA_PATH = "https://v3.fal.media/files/monkey/my_trained_miri.safetensors" # ודא שזה הנתיב הנכון שלך מ-assets.yaml

# --- פונקציית יצירה מוגנת (Retry Logic) ---
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    reraise=True
)
def generate_image_task(shot_id, prompt):
    print(f"🎨 {shot_id}: Sending to Flux...")
    
    # שליחה ל-FAL
    handler = fal_client.submit(
        FLUX_MODEL,
        arguments={
            "prompt": prompt,
            "image_size": "landscape_16_9",
            "num_inference_steps": config["pipeline"]["flux_steps"],
            "guidance_scale": 3.5,
            "loras": [{
                "path": LORA_PATH,
                "scale": 0.9
            }],
            "enable_safety_checker": False
        },
    )
    
    # המתנה לתוצאה (FAL מחזיר כתובת URL)
    result = handler.get()
    image_url = result["images"][0]["url"]
    
    # הורדת התמונה ושמירה בדיסק
    response = requests.get(image_url)
    if response.status_code == 200:
        filename = f"{shot_id}.png"
        save_path = os.path.join(config["paths"]["images_output"], filename)
        with open(save_path, "wb") as f:
            f.write(response.content)
        return {"id": shot_id, "status": "SUCCESS", "path": save_path}
    else:
        raise Exception(f"Failed to download image from {image_url}")

def process_shot(shot_id):
    shot = shots.get(shot_id)
    # רק שוטים שאושרו ע"י ג'ימיני מוכנים ליצירה
    if not shot or shot["stills"]["status"] != "APPROVED":
        return None

    # אם כבר יש תמונה, מדלגים (אלא אם רוצים לדרוס)
    if os.path.exists(os.path.join(config["paths"]["images_output"], f"{shot_id}.png")):
        # אפשר להוסיף כאן לוגיקה של "דריסה בכוח" אם רוצים
        print(f"⏩ {shot_id}: Image already exists. Skipping.")
        return None

    # קריאת הפרומפט המאושר
    prompt_path = shot["stills"]["prompt_file"]
    if not os.path.exists(prompt_path): return None
    
    with open(prompt_path, "r", encoding="utf-8") as f: prompt = f.read()

    try:
        return generate_image_task(shot_id, prompt)
    except Exception as e:
        return {"id": shot_id, "status": "ERROR", "msg": str(e)}

def main():
    # איסוף שוטים מוכנים
    ready_shots = [sid for sid, data in shots.items() if data["stills"]["status"] == "APPROVED"]
    
    if not ready_shots:
        print("🤷 No approved shots ready for generation.")
        return

    print(f"🚀 Starting Flux Generation for {len(ready_shots)} shots...")
    print(f"💳 Fal.ai Mode: Parallel Generation Enabled")

    # קביעת מספר התהליכים במקביל
    # אם שילמת ב-FAL, אתה יכול לנסות 5-10. אם אתה בחינם/בסיסי, עדיף 2-3.
    # נגדיר 5 כברירת מחדל אופטימלית
    MAX_CONCURRENCY = 5 
    
    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
        future_to_shot = {executor.submit(process_shot, sid): sid for sid in ready_shots}
        
        for future in as_completed(future_to_shot):
            res = future.result()
            if res:
                if res["status"] == "SUCCESS":
                    print(f"✅ {res['id']}: Generated successfully -> {res['path']}")
                    # עדכון ה-JSON
                    shots[res['id']]["stills"]["image_path"] = res["path"]
                    shots[res['id']]["stills"]["status"] = "IMAGE_READY"
                elif res["status"] == "ERROR":
                    print(f"❌ {res['id']}: Failed - {res['msg']}")

    # שמירה סופית
    print("💾 Saving DB...")
    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)
    
    print("🏁 Generation complete.")

if __name__ == "__main__":
    main()