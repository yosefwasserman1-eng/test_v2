import json
import os
import yaml
import time
from concurrent.futures import ThreadPoolExecutor
from claude_client import get_claude_response

# --- הגדרות נתיבים ---
CONFIG_PATH = "config.yaml"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def generate_prompt_for_shot(shot_id, shot_data, scene_data, assets):
    """
    בונה את הבקשה לקלוד עבור שוט ספציפי - עם לוגיקת 'Start Frame'
    """
    # 1. איסוף המידע
    visual_brief = shot_data['brief']['visual']
    motion_brief = shot_data['brief']['motion']
    
    # שליפת תיאורי נכסים
    loc_id = scene_data.get('location_id')
    ward_id = scene_data.get('wardrobe_id')
    
    loc_desc = assets['locations'].get(loc_id, {}).get('description', loc_id)
    ward_desc = assets['wardrobe'].get(ward_id, {}).get('description', ward_id)
    
    moods = ", ".join(scene_data.get('mood_keywords', []))
    constraints = shot_data.get('constraints', {})

    # 2. בניית הסיסטם פרומפט - משודרג לטיפול בבעיית ה-Start Frame
    system_prompt = """
    You are an Expert Cinematographer and Prompt Engineer for Flux.1 AI.
    Your Goal: Create the STATIC START FRAME (Time=0) for a video generation process.
    
    CRITICAL LOGIC RULE (THE "T=0" RULE):
    You will receive a description of an ACTION (Motion). 
    Your job is to describe the state *BEFORE* that action completes.
    
    EXAMPLES:
    - Input: "Miri lights the candle." -> Output Prompt must show: "Miri holding an UNLIT candle near a flame/match." (NOT a lit candle).
    - Input: "Miri opens the door." -> Output Prompt must show: "Miri reaching for the handle of a CLOSED door."
    - Input: "Miri bursts into tears." -> Output Prompt must show: "Miri looking sad, eyes welling up, but no tears falling yet."
    
    OUTPUT RULES:
    1. OUTPUT ONLY THE RAW PROMPT. No introductions.
    2. STYLE: 1850s Period Piece, Cinematic, 8k, Hyper-realistic, Eastern Europe atmosphere.
    3. INJECT DETAILS: Use the Location and Wardrobe descriptions precisely.
    4. LIGHTING: Translates 'mood keywords' into specific lighting terms.
    5. CAMERA: Respect the constraints (Close Up, Wide Shot, Low Angle).
    """

    user_message = f"""
    --- DIRECTOR'S BRIEF ---
    VISUAL ACTION (The Subject): {visual_brief}
    REQUIRED MOTION (What will happen next): {motion_brief}
    
    --- ASSETS ---
    LOCATION: {loc_desc}
    WARDROBE: {ward_desc}
    MOOD: {moods}
    TECHNICAL CONSTRAINTS: {constraints}
    
    --- TASK ---
    Write the Flux Prompt for the START FRAME (T=0). 
    Remember: If the action changes the state of an object, describe the INITIAL state.
    """

    print(f"🧠 Claude is calculating T=0 state for {shot_id}...")
    
    # שליחה לקלוד
    try:
        prompt_text = get_claude_response(system_prompt, user_message)
        return shot_id, prompt_text.strip()
    except Exception as e:
        print(f"❌ Failed to generate {shot_id}: {e}")
        return shot_id, None

def main():
    config = load_config()
    
    # טעינת דאטה
    with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)
    with open(config["paths"]["scenes_db"], "r", encoding="utf-8") as f: scenes = json.load(f)
    with open(config["paths"]["assets"], "r", encoding="utf-8") as f: assets = yaml.safe_load(f)

    # יצירת משימות
    tasks = []
    for sid, data in shots.items():
        if data["stills"]["status"] == "PENDING": # או סטטוס אחר אם תרצה לשכתב קיימים
            scene_ref = data["scene_ref"]
            if scene_ref in scenes:
                tasks.append((sid, data, scenes[scene_ref]))

    if not tasks:
        print("🎉 No pending shots found.")
        return

    print(f"🚀 Starting T=0 Prompt Generation for {len(tasks)} shots...")

    # הרצה במקביל
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(generate_prompt_for_shot, t[0], t[1], t[2], assets)
            for t in tasks
        ]

        for future in futures:
            sid, prompt_result = future.result()
            if prompt_result:
                # שמירה
                prompt_path = shots[sid]["stills"]["prompt_file"]
                os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(prompt_result)
                
                shots[sid]["stills"]["status"] = "PROMPT_READY"
                print(f"✅ {sid} Prompt Saved!")

    # עדכון DB
    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)
    
    print("\n🏁 Process Complete.")

if __name__ == "__main__":
    main()