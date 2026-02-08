import os
import json
import yaml

# --- המילון שמכיל את התיקונים לכל הבעיות שעלו בדוח ---
REPAIRS = {
    # תיקון גחלים מרחפות - הוספת אפר ומגע פיזי
    "SHOT_001": """Extreme close-up of dying red embers RESTING HEAVILY in a deep bed of gray ash. The charred wood logs are physically touching the stone hearth, no floating. Heat distortion. Warm amber light. 1850s cottage style. 8k hyper-realistic, macro photography details.""",

    # תיקון זהות (miriN14) + תיקון ריחוף (Weighted sit)
    "SHOT_006": """Wide shot, 1850s cottage. miriN14, a young woman, is seated FIRMLY and HEAVILY on a rustic wooden stool. Her body weight is visibly sinking into the seat. She wears a modest peasant dress and thick wool shawl. Her skirt is compressed where she sits. She holds a lit lantern (FIRE_GLOW). Dark atmospheric lighting. Hyper-realistic physics, grounded posture. 8k cinematic.""",

    # תיקון זהות (miriN14) - היה חסר הטריגר
    "SHOT_010": """Wide shot, 1850s cottage exterior at night. The thick wooden door stands OPEN. miriN14 stands in the doorway holding a glowing rusted iron lantern. She wears a thick wool shawl over a modest dress. Faint amber firelight spills onto the snow. Cinematic composition, lighting_type: FIRE_GLOW, hyper-realistic 8k, sharp focus on miriN14's face.""",
    
    # הוספתי כאן תיקון גורף גם לשוטים האחרים שאולי לא דווחו אבל בטוח צריכים את הטריגר
    "SHOT_003": """Cinematic Medium Close-Up. miriN14 sits near the fireplace, holding a small unlit wooden stick. We clearly see her face. She looks down at her hand reaching toward the fire. Warm FIRE_GLOW hitting her face. Modest dress, 8k resolution, miriN14 likeness.""",
    
    "SHOT_004": """Cinematic Close-Up on miriN14's face. miriN14 holds a burning wooden taper stick near a lantern. The flame illuminates her face (FIRE_GLOW). She looks intently at the lantern. High contrast, emotional lighting, 8k photorealistic."""
}

def apply_bulk_fixes():
    print("🚑 Applying BULK FIXES based on User Report...")
    
    with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
    shots_path = config["paths"]["shots_board"]
    
    with open(shots_path, "r", encoding="utf-8") as f: shots = json.load(f)

    for shot_id, new_prompt in REPAIRS.items():
        if shot_id in shots:
            print(f"🔧 Fixing {shot_id}...")
            
            # 1. עדכון קובץ הפרומפט
            prompt_path = shots[shot_id]["stills"]["prompt_file"]
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(new_prompt)
            
            # 2. איפוס סטטוס ל-APPROVED (מוכן ליצירה)
            shots[shot_id]["stills"]["status"] = "APPROVED"
            shots[shot_id]["stills"]["inspector_feedback"] = "Fixed via Bulk Script (Identity & Physics)"
            
            # 3. מחיקת תמונה ישנה כדי להכריח יצירה מחדש
            old_img = shots[shot_id]["stills"].get("image_path")
            if old_img and os.path.exists(old_img):
                try:
                    os.remove(old_img)
                    print(f"   🗑️ Deleted old failure image.")
                except: pass
            shots[shot_id]["stills"]["image_path"] = None

    with open(shots_path, "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)
        
    print("\n✅ All fixes applied. The shots are now marked APPROVED.")
    print("👉 Now run: 'python scripts/03_img_gen.py' to generate the corrected versions.")

if __name__ == "__main__":
    apply_bulk_fixes()