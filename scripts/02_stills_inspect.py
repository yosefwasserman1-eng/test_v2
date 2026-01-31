import os
import json
import yaml
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()

# הגדרת הלקוח החדש
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# טעינת קונפיגורציה
with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)

# טעינת הלוח
with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

# הגדרת המודל
GEMINI_MODEL_NAME = config.get("models", {}).get("gemini", "gemini-1.5-flash")

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
   - **CRITICAL:** If the prompt describes the *result*, REWRITE it to be the *start*.
"""

def process_single_shot(shot_id):
    """
    פונקציה המטפלת בשוט בודד - מיועדת לרוץ בתוך Thread
    """
    shot = shots.get(shot_id)
    if not shot: return None

    # רק שוטים שמחכים לבדיקה
    if shot["stills"]["status"] != "PROMPT_READY":
        return None

    prompt_path = shot["stills"]["prompt_file"]
    if not os.path.exists(prompt_path): return None

    with open(prompt_path, "r", encoding="utf-8") as f: current_prompt = f.read()

    visual_brief = shot['brief']['visual']
    motion_brief = shot['brief']['motion']
    constraints = json.dumps(shot.get('constraints', {}))

    try:
        # בניית הפרומפט למודל
        full_sys_prompt = f"""
        SYSTEM ALERT: CURRENT DATE IS JANUARY 31, 2026.
        ROLE: Production Supervisor & Prompt Fixer.
        
        --- RULES ---
        {TZNIUT_RULES}
        {VIDEO_LOGIC_RULES}
        
        3. TECHNICAL CONSTRAINTS: {constraints}
           
        --- CONTEXT ---
        ORIGINAL BRIEF: {visual_brief}
        MOTION: {motion_brief}
        
        INPUT PROMPT:
        {current_prompt}
        
        OUTPUT ONLY THE FINAL RAW PROMPT TEXT.
        """

        # שליחה למודל (New SDK)
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=full_sys_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        
        corrected_prompt = response.text.strip()
        
        # שמירת הקובץ (Thread Safe כי כל תהליך כותב לקובץ אחר)
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(corrected_prompt)
        
        return {
            "id": shot_id,
            "status": "APPROVED",
            "msg": "Checked by GenAI (Parallel)"
        }

    except Exception as e:
        return {
            "id": shot_id,
            "status": "ERROR",
            "msg": str(e)
        }

def main():
    # איסוף כל השוטים שצריכים בדיקה
    pending_shots = [sid for sid, data in shots.items() if data["stills"]["status"] == "PROMPT_READY"]
    
    if not pending_shots:
        print("🎉 No prompts waiting for inspection.")
        return

    print(f"🚀 Starting PARALLEL inspection for {len(pending_shots)} shots...")
    print(f"💳 Paid Account Detected: Unlocking limits.")

    # הרצה במקביל - 10 תהליכים בו זמנית
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # שליחת כל המשימות
        future_to_shot = {executor.submit(process_single_shot, sid): sid for sid in pending_shots}
        
        for future in as_completed(future_to_shot):
            res = future.result()
            if res:
                results.append(res)
                if res["status"] == "APPROVED":
                    print(f"✅ {res['id']}: Approved.")
                    # עדכון הזיכרון הראשי (JSON object)
                    shots[res['id']]["stills"]["status"] = "APPROVED"
                    shots[res['id']]["stills"]["inspector_feedback"] = res["msg"]
                else:
                    print(f"❌ {res['id']}: Failed - {res['msg']}")

    # שמירה אחת מרוכזת בסוף התהליך (מונע התנגשויות כתיבה)
    print("💾 Saving all changes to DB...")
    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)
    
    print("🏁 Batch inspection finished.")

if __name__ == "__main__":
    main()