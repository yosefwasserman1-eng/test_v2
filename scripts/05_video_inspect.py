import os
import json
import yaml
import google.generativeai as genai
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# טעינת קונפיגורציה
with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

# שליפת שם המודל מהקונפיג (סנכרון מלא עם הסטנדרט החדש)
GEMINI_MODEL_NAME = config.get("models", {}).get("gemini", "gemini-3-flash")

# --- חוקי הברזל לוידאו (Physics & AI Artifacts Prevention) ---
VIDEO_SAFETY_RULES = """
1. NO MORPHING: Objects cannot change into other objects (e.g., a stick cannot become a snake).
2. SLOW MOTION PREFERRED: High speed action causes blur/artifacts in AI video generation.
3. CAMERA STABILITY: Do not ask for conflicting moves (e.g., "Zoom in AND Pan Left" simultaneously).
4. CONSISTENCY: The action must match the static image context (Start Frame).
5. NO VIOLENCE/GORE: Strict safety policy.
"""

def inspect_video_prompt(shot_id):
    shot = shots.get(shot_id)
    if not shot: return

    # בדיקת קיום קובץ פרומפט לוידאו
    prompt_path = shot["video"]["prompt_file"]
    if not os.path.exists(prompt_path):
        print(f"⚠️ Video prompt file missing for {shot_id}")
        return

    with open(prompt_path, "r", encoding="utf-8") as f: current_prompt = f.read()

    # שליפת הקשר (Context) מהשוט המקורי
    visual_brief = shot['brief']['visual']
    motion_brief = shot['brief']['motion']

    print(f"🛡️ Inspecting VIDEO prompt for {shot_id} using {GEMINI_MODEL_NAME}...")
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        
        sys_prompt = f"""
        ROLE: AI Video Production Supervisor for Kling Model.
        
        YOUR TASK: Review and Optimize the Video Generation Prompt.
        
        --- SAFETY & PHYSICS RULES ---
        {VIDEO_SAFETY_RULES}
        
        --- CONTEXT ---
        ORIGINAL VISUAL: {visual_brief}
        REQUIRED MOTION: {motion_brief}
        
        --- INSTRUCTIONS ---
        1. Check if the prompt asks for "Fast running" or complex fighting -> TONE IT DOWN to "Jogging" or "Tense stance" (Fast motion fails in AI).
        2. Ensure Camera movements are cinematic and simple.
        3. If the prompt contradicts the Start Frame logic -> Fix it.
        4. If the prompt is good -> Output it as is.
        
        OUTPUT ONLY THE FINAL OPTIMIZED PROMPT TEXT.
        """
        
        response = model.generate_content(f"{sys_prompt}\n\nINPUT PROMPT:\n{current_prompt}")
        corrected_prompt = response.text.strip()
        
        # שמירה
        with open(prompt_path, "w", encoding="utf-8") as f: f.write(corrected_prompt)
        
        # אישור
        shot["video"]["status"] = "VIDEO_READY" # זה הסטטוס שמאותת למחולל הוידאו (06) להתחיל לעבוד
        shot["video"]["inspector_feedback"] = f"Optimized by {GEMINI_MODEL_NAME}"
        
        # עדכון ה-DB
        with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
            json.dump(shots, f, indent=4, ensure_ascii=False)
            
        print(f"✅ {shot_id} Video Prompt Optimized & Approved.")
        
    except Exception as e:
        print(f"❌ Error inspecting {shot_id}: {e}")

def main():
    # בדיקת כמות עדכונים
    updates = 0
    
    # אופציה להרצה ידנית או אוטומטית
    print("running auto-scan for 'PROMPT_READY' video shots...")
    
    for sid, data in shots.items():
        # הוא בודק רק שוטים שסיימו את שלב הכתיבה (04) ומחכים לבדיקה
        if data["video"]["status"] == "PROMPT_READY":
            inspect_video_prompt(sid)
            updates += 1
            
    if updates == 0:
        print("🤷 No video prompts waiting for inspection.")
    else:
        print(f"🏁 Finished inspecting {updates} video prompts.")

if __name__ == "__main__":
    main()