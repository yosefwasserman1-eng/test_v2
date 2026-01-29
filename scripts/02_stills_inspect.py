import os
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
TZNIUT_RULES = """
1. Sleeves must cover elbows (Long sleeves).
2. Neckline must be high (Clavicle covered).
3. Skirt must cover knees (Midi/Maxi length).
4. Fit must be loose, not tight.
"""

def inspect_prompt(shot_id):
    shot = shots.get(shot_id)
    if not shot: return
    
    prompt_path = shot["stills"]["prompt_file"]
    with open(prompt_path, "r", encoding="utf-8") as f:
        current_prompt = f.read()

    print(f"🕵️ Inspecting prompt for {shot_id}...")
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # סיסטם פרומפט אגרסיבי לתיקון
    sys_prompt = f"""
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
    """
    
    response = model.generate_content(f"{sys_prompt}\n\nINPUT PROMPT:\n{current_prompt}")
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
