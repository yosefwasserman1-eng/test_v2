import os
import json
import yaml
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# חוקי הברזל לוידאו ב-AI
VIDEO_SAFETY_RULES = """
1. NO MORPHING: Objects cannot change into other objects.
2. SLOW MOTION PREFERRED: High speed action causes blur/artifacts in AI video.
3. CAMERA STABILITY: Don't ask for "zoom in AND pan left AND rotate" simultaneously.
4. CONSISTENCY: The action must match the static image context.
5. NO VIOLENCE/GORE: Strict safety policy.
"""

def inspect_video_prompt(shot_id, shots, config):
    shot = shots.get(shot_id)
    prompt_path = shot["video"]["prompt_file"]
    
    if not os.path.exists(prompt_path): return

    with open(prompt_path, "r", encoding="utf-8") as f: current_prompt = f.read()

    print(f"🛡️ Inspecting VIDEO prompt for {shot_id}...")
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    sys_prompt = f"""
    ROLE: AI Video Supervisor for Kling Model.
    
    YOUR TASK:
    1. Check against these rules:
    {VIDEO_SAFETY_RULES}
    
    2. SPECIFIC CHECK:
    - If the prompt asks for "Fast running" or "Complex fighting", TONE IT DOWN to "Jogging" or "Tense stance". Fast motion fails in AI.
    
    3. OUTPUT:
    - Return the OPTIMIZED prompt that is safe and likely to yield high quality video.
    """
    
    try:
        response = model.generate_content(f"{sys_prompt}\n\nINPUT PROMPT:\n{current_prompt}")
        corrected_prompt = response.text.strip()
        
        # שמירה
        with open(prompt_path, "w", encoding="utf-8") as f: f.write(corrected_prompt)
        
        # אישור
        shot["video"]["status"] = "VIDEO_READY" # מוכן ליצירה!
        shot["video"]["inspector_feedback"] = "Optimized by Gemini Video Guard"
        print(f"✅ {shot_id} Video Prompt Optimized & Approved.")
        
    except Exception as e:
        print(f"❌ Error inspecting {shot_id}: {e}")

def main():
    with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
    with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)
    
    # עוברים על כל השוטים שממתינים לבדיקת וידאו
    updates = 0
    for sid, data in shots.items():
        if data["video"]["status"] == "PROMPT_READY":
            inspect_video_prompt(sid, shots, config)
            updates += 1
            
    if updates > 0:
        with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
            json.dump(shots, f, indent=4, ensure_ascii=False)
        print(f"🏁 Finished inspecting {updates} video prompts.")
    else:
        print("🤷 No video prompts waiting for inspection.")

if __name__ == "__main__":
    main()