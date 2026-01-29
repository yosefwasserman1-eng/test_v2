import os

# --- תוכן הקבצים המשודרגים ---

# 1. המחולל (עם תמיכה בזהות)
IMG_GEN_CONTENT = """import os
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
"""

# 2. המשגיח (עם הזרקת צניעות)
INSPECT_CONTENT = """import os
import json
import yaml
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
with open(config["paths"]["assets"], "r", encoding="utf-8") as f: assets = yaml.safe_load(f)
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

# --- חוקי הברזל (מוזרקים לקוד למקרה שאין ב-yaml) ---
TZNIUT_RULES = \"\"\"
1. Sleeves must cover elbows (Long sleeves).
2. Neckline must be high (Clavicle covered).
3. Skirt must cover knees (Midi/Maxi length).
4. Fit must be loose, not tight.
\"\"\"

def inspect_prompt(shot_id):
    shot = shots.get(shot_id)
    if not shot: return
    
    prompt_path = shot["stills"]["prompt_file"]
    with open(prompt_path, "r", encoding="utf-8") as f:
        current_prompt = f.read()

    print(f"🕵️ Inspecting prompt for {shot_id}...")
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # סיסטם פרומפט אגרסיבי לתיקון
    sys_prompt = f\"\"\"
    ROLE: Tzniut (Modesty) Supervisor & Prompt Enhancer.
    
    YOUR TASK:
    1. Check if the prompt violates these rules:
    {TZNIUT_RULES}
    
    2. IF VIOLATION DETECTED:
       - Rewrite the prompt to fix it (e.g., change "short sleeves" to "long sleeves").
       
    3. IF NO VIOLATION:
       - Output the prompt as is (or slightly enhance quality keywords).
       
    4. CRITICAL: 
       - Ensure specific constraints from JSON are met: {json.dumps(shot.get('constraints', {}))}
       
    OUTPUT ONLY THE CORRECTED PROMPT TEXT. NO CHAT.
    \"\"\"
    
    response = model.generate_content(f"{sys_prompt}\\n\\nINPUT PROMPT:\\n{current_prompt}")
    corrected_prompt = response.text.strip()
    
    # שמירת התיקון
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(corrected_prompt)
        
    # עדכון סטטוס
    shot["stills"]["status"] = "APPROVED"
    shot["stills"]["inspector_feedback"] = "Auto-corrected by Gemini"
    
    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)
        
    print("✅ Prompt Approved & Optimized.")

if __name__ == "__main__":
    sid = input("Enter Shot ID to Inspect: ").strip()
    inspect_prompt(sid)
"""

# 3. המתקן (היברידי - טקסט או מסיכה)
REPAIR_CONTENT = """import os
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
"""

# יצירת הקבצים בתיקיית scripts
SCRIPTS = {
    "scripts/03_img_gen.py": IMG_GEN_CONTENT,
    "scripts/02_stills_inspect.py": INSPECT_CONTENT,
    "scripts/repair_shot.py": REPAIR_CONTENT
}

def install_upgrades():
    if not os.path.exists("scripts"):
        os.makedirs("scripts")
        
    for path, content in SCRIPTS.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Created/Updated: {path}")
        
    print("\\n🚀 Upgrades Installed!")
    print("⚠️  IMPORTANT ACTION REQUIRED:")
    print("1. Open 'assets/assets.yaml'")
    print("2. Add this line under the root:")
    print("   face_reference_path: 'assets/miri_face_ref.jpg'")
    print("3. Make sure you put a real image of Miri in that path!")

if __name__ == "__main__":
    install_upgrades()