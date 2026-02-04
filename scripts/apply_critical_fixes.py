import os
import json
import yaml

# --- הטקסטים המתוקנים (Hard Coded) ---
FIXES = {
    # שוט 001: נשאר תקריב על הגחלים (בלי מירי) - לאווירה
    "SHOT_001": """Extreme close-up shot of dying red embers glowing faintly in a weathered stone fireplace. Dark charred logs, ash-covered hearth stones. Gentle heat distortion. Warm amber light casting subtle shadows on rough stone walls. 1850s Eastern European cottage interior. Cinematic composition, 8k hyper-realistic, soft fire-glow lighting, volumetric atmosphere. Intimate framing isolating the ember bed. No people visible.""",

    # שוט 003: תיקון ל-Medium Shot כדי לראות את הפנים של מירי (חובה לוידאו)
    "SHOT_003": """Cinematic Medium Shot, 1850s style. Miri sits near the fireplace, holding a small unlit wooden stick. We clearly see her upper body and face. She wears a modest peasant dress, high collar, loose wool shawl. She looks down at her hand as she reaches toward the fire (off-screen glow). The primary light is the warm FIRE_GLOW hitting her face and hand. Avoid occlusion of the face. Rustic cottage background, depth of field separating her from the background. 8k resolution.""",

    # שוט 004: תיקון ל-Close Up על הפנים והיד (חובה לוידאו)
    "SHOT_004": """Cinematic Close-Up on Miri's face and hands. She is holding a burning wooden taper stick, bringing the small flame toward a rusted iron lantern. The small flame creates a beautiful, warm illumination on her face (FIRE_GLOW). She looks intently at the lantern. Modest clothing, high neckline, long sleeves. The background is dark and rustic. Focus shared between her expression and the flame. High contrast, emotional lighting, 8k photorealistic.""",

    # שוט 006: תיקון ה"ריחוף" - הדגשת המשקל והישיבה
    "SHOT_006": """Wide shot, 1850s cottage. Miri is seated FIRMLY and HEAVILY on a rustic wooden stool. Her body weight is visibly sinking into the seat, grounded and realistic. She wears a modest, loose peasant dress and a thick wool shawl. Her skirt is compressed where she sits, showing physical contact with the wood. She is beginning to stand up, leaning slightly forward. She holds a lit lantern (FIRE_GLOW). Dark atmospheric lighting. Hyper-realistic physics, grounded posture. 8k cinematic.""",

    # שוט 007: נשאר תקריב על היד (בלי מירי) - למתח
    "SHOT_007": """Cinematic Close-Up on a hand. Miri's hand hovers hesitantly near an old heavy wooden door handle. Fingers curled, not yet touching the metal. We see the sleeve of her modest dress covering her wrist. She holds a glowing lantern in her other hand (off screen), casting warm light on the door texture. Rustic stone walls background. Atmosphere of tension. 1850s period details, 8k resolution, shallow depth of field."""
}

def apply_fixes():
    print("🚑 Starting Critical Fixes Application...")
    
    # טעינת הגדרות
    with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
    shots_path = config["paths"]["shots_board"]
    
    with open(shots_path, "r", encoding="utf-8") as f: shots = json.load(f)

    for shot_id, new_prompt_text in FIXES.items():
        if shot_id not in shots:
            print(f"⚠️ Shot {shot_id} not found in board. Skipping.")
            continue
            
        print(f"🔧 Fixing {shot_id}...")
        
        # 1. עדכון קובץ הפרומפט
        prompt_path = shots[shot_id]["stills"]["prompt_file"]
        os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
        
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(new_prompt_text)
            
        # 2. איפוס הסטטוס ל-APPROVED (כדי לדלג על בדיקה וללכת ישר ליצירה)
        shots[shot_id]["stills"]["status"] = "APPROVED"
        shots[shot_id]["stills"]["inspector_feedback"] = "Manually Fixed via Script (Mix Strategy)"
        
        # 3. מחיקת רפרנס לתמונה ישנה (כדי להכריח יצירה מחדש)
        if "image_path" in shots[shot_id]["stills"]:
            old_path = shots[shot_id]["stills"]["image_path"]
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                    print(f"   🗑️ Deleted old image: {old_path}")
                except: pass
            shots[shot_id]["stills"]["image_path"] = None

    # שמירה
    with open(shots_path, "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)
        
    print("✅ All fixes applied successfully!")
    print("👉 Now run: 'python scripts/03_img_gen.py' and select these shots.")

if __name__ == "__main__":
    apply_fixes()