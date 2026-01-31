import os
import json
import yaml
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# טעינת משתני סביבה
load_dotenv()

# הגדרת הלקוח החדש
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# טעינת הגדרות
with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

# שימוש במודל העדכני (אם לא מוגדר בקונפיג)
GEMINI_MODEL_NAME = config.get("models", {}).get("gemini", "gemini-3-flash-preview")

# --- חוקי הברזל ---
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

# --- פונקציית עזר מוגנת (Wrapper) ---
# אם נכשלים בגלל עומס - מחכים 20 שניות ומנסים שוב, בזמן עולה
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=20, max=120))
def call_gemini_safe(model, contents):
    return client.models.generate_content(
        model=model,
        contents=contents
    )

def inspect_prompt(shot_id):
    shot = shots.get(shot_id)
    if not shot: 
        print(f"❌ Shot {shot_id} not found.")
        return
    
    prompt_path = shot["stills"]["prompt_file"]
    if not os.path.exists(prompt_path):
        print(f"⚠️ Prompt file missing for {shot_id}")
        return

    with open(prompt_path, "r", encoding="utf-8") as f:
        current_prompt = f.read()

    visual_brief = shot['brief']['visual']
    motion_brief = shot['brief']['motion']
    constraints = json.dumps(shot.get('constraints', {}))

    print(f"🕵️ Inspecting prompt for {shot_id} using {GEMINI_MODEL_NAME}...")
    
    try:
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
        - If the prompt violates T=0 Logic -> FIX IT.
        - If the prompt is good -> Output it as is.
        
        OUTPUT ONLY THE FINAL RAW PROMPT TEXT. NO EXPLANATIONS.
        """
        
        # שימוש בפונקציה המוגנת במקום קריאה ישירה
        response = call_gemini_safe(GEMINI_MODEL_NAME, f"{sys_prompt}\n\nINPUT PROMPT:\n{current_prompt}")

        corrected_prompt = response.text.strip()
        
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(corrected_prompt)
            
        shot["stills"]["status"] = "APPROVED"
        shot["stills"]["inspector_feedback"] = f"Checked by {GEMINI_MODEL_NAME}"
        
        with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
            json.dump(shots, f, indent=4, ensure_ascii=False)
            
        print(f"✅ {shot_id}: Approved & Optimized.")
        
    except Exception as e:
        print(f"❌ Error inspecting {shot_id}: {e}")

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
                # המתנה מנומסת בין בקשות כדי לא להרגיז את ה-API
                print("⏳ Cooling down for 5 seconds...")
                time.sleep(5)
        
        if count == 0:
            print("🎉 No prompts waiting for inspection.")