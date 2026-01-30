import os
import json
import yaml
import google.generativeai as genai
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# טעינת הגדרות
with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

# שליפת מודל ג'ימיני מהקונפיג (עם גיבוי למקרה חרום)
GEMINI_MODEL_NAME = config.get("models", {}).get("gemini", "gemini-3-flash")

# --- חוקי הברזל (צניעות + לוגיקת וידאו) ---
TZNIUT_RULES = """
1. MODESTY (TZNIUT):
   - Sleeves must cover elbows (Long sleeves).
   - Neckline must be high (Clavicle covered).
   - Skirt must cover knees (Midi/Maxi length).
   - Fit must be loose, not tight.
"""

VIDEO_LOGIC_RULES = """
2. VIDEO START-FRAME LOGIC (T=0):
   - This image is the STARTING POINT for a video generation.
   - It must depict the state *BEFORE* the action is completed.
   - Example: If Action is "Lighting a candle", image must show "Unlit candle".
   - Example: If Action is "Opening a door", image must show "Closed door + Hand reaching".
   - **CRITICAL:** If the prompt describes the *result* (e.g., "Lit candle"), REWRITE it to be the *start* (e.g., "Unlit candle").
"""

def inspect_prompt(shot_id):
    shot = shots.get(shot_id)
    if not shot: 
        print(f"❌ Shot {shot_id} not found.")
        return
    
    # בדיקה שיש קובץ פרומפט
    prompt_path = shot["stills"]["prompt_file"]
    if not os.path.exists(prompt_path):
        print(f"⚠️ Prompt file missing for {shot_id}")
        return

    with open(prompt_path, "r", encoding="utf-8") as f:
        current_prompt = f.read()

    # שליפת הבריף
    visual_brief = shot['brief']['visual']
    motion_brief = shot['brief']['motion']
    constraints = json.dumps(shot.get('constraints', {}))

    print(f"🕵️ Inspecting prompt for {shot_id} using {GEMINI_MODEL_NAME}...")
    
    try:
        # שימוש במודל המעודכן מהקונפיג
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        
        sys_prompt = f"""
        ROLE: Production Supervisor & Prompt Fixer.
        YOUR TASK: Review and Fix the Flux Image Prompt based on the Rules below.
        
        --- RULES ---
        {TZNIUT_RULES}
        {VIDEO_LOGIC_RULES}
        
        3. TECHNICAL CONSTRAINTS:
           - Ensure these settings are respected: {constraints}
           
        --- CONTEXT ---
        ORIGINAL BRIEF (ACTION): {visual_brief}
        REQUIRED MOTION: {motion_brief}
        
        --- INSTRUCTIONS ---
        - If the prompt violates Modesty -> FIX IT.
        - If the prompt violates T=0 Logic (shows the result instead of start) -> FIX IT.
        - If the prompt is good -> Output it as is (you can polish quality keywords).
        
        OUTPUT ONLY THE FINAL RAW PROMPT TEXT. NO EXPLANATIONS.
        """
        
        response = model.generate_content(f"{sys_prompt}\n\nINPUT PROMPT:\n{current_prompt}")
        corrected_prompt = response.text.strip()
        
        # שמירת התיקון
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(corrected_prompt)
            
        # עדכון סטטוס
        shot["stills"]["status"] = "APPROVED"
        shot["stills"]["inspector_feedback"] = f"Checked by {GEMINI_MODEL_NAME} (Modesty + T=0 Logic)"
        
        # שמירה ל-JSON
        with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
            json.dump(shots, f, indent=4, ensure_ascii=False)
            
        print(f"✅ {shot_id}: Approved & Optimized.")
        
    except Exception as e:
        print(f"❌ Error inspecting {shot_id}: {e}")
        # במקרה של שגיאה (למשל המודל חדש מידי למפתח שלך), אפשר להוסיף כאן לוגיקת Fallback

if __name__ == "__main__":
    user_input = input("Enter Shot ID (or press Enter to inspect ALL pending prompts): ").strip()
    
    if user_input:
        inspect_prompt(user_input)
    else:
        count = 0
        for sid, data in shots.items():
            if data["stills"]["status"] == "PROMPT_READY":
                inspect_prompt(sid)
                count += 1
        
        if count == 0:
            print("🎉 No prompts waiting for inspection.")