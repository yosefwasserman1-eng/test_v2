import os
import json
import yaml
import fal_client
from dotenv import load_dotenv

load_dotenv()

# טעינת הגדרות
with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
with open(config["paths"]["assets"], "r", encoding="utf-8") as f: assets = yaml.safe_load(f)
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

def generate_image(shot_id):
    print(f"🎨 Generating {shot_id}...")
    shot = shots.get(shot_id)
    if not shot or shot["stills"]["status"] != "APPROVED":
        print("❌ Shot not ready or not approved.")
        return

    # קריאת הפרומפט המוכן
    with open(shot["stills"]["prompt_file"], "r", encoding="utf-8") as f:
        final_prompt = f.read()

    # הגדרות ל-FAL
    args = {
        "prompt": final_prompt,
        "image_size": config["pipeline"].get("image_size", "landscape_16_9"),
        "loras": [{"path": assets["lora_url"], "scale": 1.0}],
        "num_inference_steps": config["pipeline"].get("flux_steps", 28),
        "enable_safety_checker": True,
        "output_format": "jpeg"
    }

    # --- שדרוג 1: הזרקת תמונת רפרנס (Identity Lock) ---
    # בודק אם הוגדר נתיב ב-assets.yaml
    ref_path = assets.get("face_reference_path")
    if ref_path and os.path.exists(ref_path):
        print(f"🔒 Locking Identity using: {ref_path}")
        ref_url = fal_client.upload_file(ref_path)
        args["image_prompts"] = [
            {"image_url": ref_url, "type": "image_prompt", "weight": 0.85}
        ]
    # ----------------------------------------------------

    try:
        result = fal_client.submit(config["models"]["flux"], arguments=args).get()
        image_url = result["images"][0]["url"]
        
        # שמירה
        version = shot["stills"].get("version", 0) + 1
        filename = f"{shot_id}_v{version}.jpg"
        save_path = os.path.join(config["paths"]["images_output"], filename)
        
        import requests
        with open(save_path, "wb") as f:
            f.write(requests.get(image_url).content)
            
        # עדכון ה-JSON
        shot["stills"]["image_path"] = save_path
        shot["stills"]["status"] = "IMAGE_READY"
        shot["stills"]["version"] = version
        
        with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
            json.dump(shots, f, indent=4, ensure_ascii=False)
            
        print(f"✅ Saved to {save_path}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    sid = input("Enter Shot ID (e.g., SHOT_001): ").strip()
    generate_image(sid)
