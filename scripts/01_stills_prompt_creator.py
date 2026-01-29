import json
import os
import yaml
import time
from concurrent.futures import ThreadPoolExecutor
from claude_client import get_claude_response  # ייבוא מהקובץ שיצרנו בשלב 1

# --- הגדרות נתיבים ---
CONFIG_PATH = "config.yaml"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def generate_prompt_for_shot(shot_id, shot_data, scene_data, assets):
    """
    בונה את הבקשה לקלוד עבור שוט ספציפי
    """
    # 1. איסוף המידע
    visual_brief = shot_data['brief']['visual']
    motion_brief = shot_data['brief']['motion']
    
    # שליפת תיאורי נכסים (אם קיימים)
    loc_id = scene_data.get('location_id')
    ward_id = scene_data.get('wardrobe_id')
    
    loc_desc = assets['locations'].get(loc_id, {}).get('description', loc_id)
    ward_desc = assets['wardrobe'].get(ward_id, {}).get('description', ward_id)
    
    moods = ", ".join(scene_data.get('mood_keywords', []))
    constraints = shot_data.get('constraints', {})

    # 2. בניית הסיסטם פרומפט (המומחיות של קלוד)
    system_prompt = """
    You are an Expert Cinematographer and Prompt Engineer for Flux.1 AI.
    Your Goal: Convert a Director's Brief into a highly detailed, photorealistic image prompt.
    
    RULES:
    1. OUTPUT ONLY THE RAW PROMPT. No introductions, no "Here is the prompt".
    2. STYLE: 1850s Period Piece, Cinematic, 8k, Hyper-realistic, Eastern Europe atmosphere.
    3. INJECT DETAILS: Use the Location and Wardrobe descriptions precisely.
    4. LIGHTING: Translates 'mood keywords' into specific lighting terms (e.g., 'Volumetric', 'Chiaroscuro').
    5. CAMERA: Respect the constraints (Close Up, Wide Shot, Low Angle).
    """

    user_message = f"""
    --- INPUT DATA ---
    ACTION/VISUAL: {visual_brief}
    MOTION CONTEXT: {motion_brief}
    
    LOCATION: {loc_desc}
    WARDROBE: {ward_desc}
    MOOD: {moods}
    TECHNICAL CONSTRAINTS: {constraints}
    ------------------
    Write the Flux prompt now:
    """

    print(f"🧠 Claude is thinking about {shot_id}...")
    
    # שליחה לקלוד
    try:
        prompt_text = get_claude_response(system_prompt, user_message)
        return shot_id, prompt_text.strip()
    except Exception as e:
        print(f"❌ Failed to generate {shot_id}: {e}")
        return shot_id, None

def main():
    # טעינת קבצים
    config = load_config()
    
    with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f:
        shots = json.load(f)
    with open(config["paths"]["scenes_db"], "r", encoding="utf-8") as f:
        scenes = json.load(f)
    with open(config["paths"]["assets"], "r", encoding="utf-8") as f:
        assets = yaml.safe_load(f)

    # יצירת רשימת משימות (רק שוטים שטרם נוצרו)
    tasks = []
    for sid, data in shots.items():
        if data["stills"]["status"] == "PENDING":
            scene_ref = data["scene_ref"]
            if scene_ref in scenes:
                tasks.append((sid, data, scenes[scene_ref]))

    if not tasks:
        print("🎉 No pending shots found. All prompts reflect current data.")
        return

    print(f"🚀 Starting Batch Generation for {len(tasks)} shots...")

    # הרצה במקביל (עד 3 שוטים בו זמנית כדי לא לחרוג ממגבלות API)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(generate_prompt_for_shot, t[0], t[1], t[2], assets)
            for t in tasks
        ]

        for future in futures:
            sid, prompt_result = future.result()
            
            if prompt_result:
                # 1. שמירת קובץ הטקסט
                prompt_path = shots[sid]["stills"]["prompt_file"]
                
                # יצירת התיקייה אם אינה קיימת
                os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
                
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(prompt_result)
                
                # 2. עדכון הסטטוס בזיכרון
                shots[sid]["stills"]["status"] = "PROMPT_READY"
                print(f"✅ {sid} Prompt Saved!")

    # שמירה סופית של ה-JSON המעודכן
    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)
    
    print("\n🏁 Process Complete. You can now run the Inspector or Image Generator.")

if __name__ == "__main__":
    main()