import os
import json
import yaml
import fal_client
import requests
from dotenv import load_dotenv

load_dotenv()

with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

def repair_shot(shot_id):
    shot = shots.get(shot_id)
    current_img = shot["stills"]["image_path"]
    
    if not current_img or not os.path.exists(current_img):
        print("❌ No image found to repair.")
        return

    print(f"🔧 Repairing: {current_img}")
    print("Select Method:")
    print("1. Text Auto-Mask (e.g., 'Fix the hand')")
    print("2. Manual Mask File (Upload a black/white mask)")
    
    choice = input("Choice (1/2): ").strip()
    
    mask_url = None
    img_url = fal_client.upload_file(current_img)
    
    prompt = input("Enter Inpaint Prompt (What should be there?): ")

    if choice == "1":
        # --- אופציה 1: תיקון אוטומטי לפי טקסט ---
        what_to_fix = input("What object to fix? (e.g., 'the right hand'): ")
        print("🤖 Generating AI Mask...")
        
        res = fal_client.submit("fal-ai/segment-anything", arguments={
            "image_url": img_url,
            "prompt": what_to_fix
        }).get()
        
        if res and 'mask' in res:
            mask_url = res['mask']['url']
            print("✅ Mask generated!")
        else:
            print("❌ Failed to generate mask.")
            return

    elif choice == "2":
        # --- אופציה 2: מסיכה ידנית ---
        mask_path = input("Enter path to mask file (PNG): ").strip()
        if os.path.exists(mask_path):
            mask_url = fal_client.upload_file(mask_path)
        else:
            print("❌ Mask file not found.")
            return
            
    # ביצוע התיקון (Inpainting)
    print("🎨 Inpainting...")
    args = {
        "prompt": prompt,
        "image_url": img_url,
        "mask_url": mask_url,
        "loras": [{"path": config["models"].get("lora_url", ""), "scale": 1.0}],
        "num_inference_steps": 28,
        "strength": 0.95 # חוזק השינוי
    }
    
    # הסרנו את ה-LoRA מהארגומנטים אם הוא לא קיים בקונפיג
    # כאן אנחנו משתמשים במודל Inpainting ייעודי
    res = fal_client.submit("fal-ai/flux-lora/inpainting", arguments=args).get()
    
    # שמירת התוצאה
    new_url = res["images"][0]["url"]
    save_path = current_img.replace(".jpg", "_fixed.jpg")
    
    with open(save_path, "wb") as f:
        f.write(requests.get(new_url).content)
        
    print(f"✨ Repair Saved: {save_path}")
    
    # שאל אם לעדכן את הדאטה
    if input("Update Shot Data to use this file? (y/n): ") == 'y':
        shot["stills"]["image_path"] = save_path
        with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
            json.dump(shots, f, indent=4, ensure_ascii=False)
        print("✅ Database Updated.")

if __name__ == "__main__":
    sid = input("Enter Shot ID to Repair: ").strip()
    repair_shot(sid)
