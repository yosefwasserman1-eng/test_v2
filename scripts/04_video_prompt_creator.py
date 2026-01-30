import json
import os
import yaml
from concurrent.futures import ThreadPoolExecutor
from claude_client import get_claude_response

CONFIG_PATH = "config.yaml"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f: return yaml.safe_load(f)

def generate_video_prompt(shot_id, shot_data, scene_data):
    # שים לב: אנחנו בונים פרומפט שמתבסס על זה שיש כבר תמונה (Image-to-Video)
    visual_brief = shot_data['brief']['visual']
    motion_brief = shot_data['brief']['motion']
    moods = ", ".join(scene_data.get('mood_keywords', []))
    
    system_prompt = """
    You are an AI Video Prompt Expert for Kling AI (Image-to-Video).
    Your Goal: Write a concise motion description based on a static source image.
    
    RULES:
    1. FOCUS ON MOTION: The image already exists. Do not describe the character's looks again. Describe only WHAT MOVES.
    2. CAMERA MOVEMENT: Use professional terms (Pan, Tilt, Zoom, Push In, Rack Focus).
    3. LENGTH: Keep it under 3 sentences.
    4. PHYSICS: Ensure the motion is physically possible for a human/camera.
    5. STRUCTURE: "Camera: [Movement]. Action: [Character Movement]. Atmosphere: [Wind/Light changes]."
    """
    
    user_message = f"""
    CONTEXT:
    Static Image Subject: {visual_brief}
    Required Motion: {motion_brief}
    Mood: {moods}
    
    Write the Kling Motion Prompt:
    """

    try:
        print(f"🎥 Writing video prompt for {shot_id}...")
        prompt_text = get_claude_response(system_prompt, user_message)
        return shot_id, prompt_text.strip()
    except Exception as e:
        print(f"❌ Error {shot_id}: {e}")
        return shot_id, None

def main():
    config = load_config()
    with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)
    with open(config["paths"]["scenes_db"], "r", encoding="utf-8") as f: scenes = json.load(f)

    tasks = []
    # רצים רק על שוטים שהתמונה שלהם אושרה, אבל הוידאו טרם נכתב
    for sid, data in shots.items():
        if data["stills"]["status"] == "APPROVED" and data["video"]["status"] == "READY_FOR_PROMPT":
            tasks.append((sid, data, scenes[data["scene_ref"]]))

    if not tasks:
        print("📭 No shots ready for video prompting. (Did you approve stills in Review Board?)")
        return

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(generate_video_prompt, t[0], t[1], t[2]) for t in tasks]
        
        for future in futures:
            sid, prompt = future.result()
            if prompt:
                path = shots[sid]["video"]["prompt_file"]
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f: f.write(prompt)
                
                shots[sid]["video"]["status"] = "PROMPT_READY"
                print(f"✅ {sid} Video Prompt Saved!")

    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()