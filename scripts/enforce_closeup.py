import os
import json
import yaml
import re

def enforce_proximity():
    print("🔍 Inspecting prompts for 'Distance' issues...")
    
    with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
    with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)

    changed_count = 0

    for shot_id, data in shots.items():
        prompt_path = data["stills"]["prompt_file"]
        if not os.path.exists(prompt_path): continue
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            original_prompt = f.read()
        
        new_prompt = original_prompt
        
        # 1. החלפת "Wide Shot" ב-"Medium Close-Up"
        # המודל נוטה להתרחק כשהוא רואה Wide, אז נחליף את זה.
        new_prompt = re.sub(r'(?i)wide shot', 'Cinematic Medium Close-Up', new_prompt)
        new_prompt = re.sub(r'(?i)extreme wide shot', 'Medium Shot', new_prompt)
        new_prompt = re.sub(r'(?i)full body', 'Waist-up shot', new_prompt)
        
        # 2. הוספת מילות חיזוק לפרטים בפנים (אם הן לא קיימות)
        keywords = ", sharp focus on eyes, highly detailed face, close proximity to camera"
        if "sharp focus on eyes" not in new_prompt:
            new_prompt = new_prompt.strip() + keywords

        # 3. בדיקה אם בוצע שינוי
        if new_prompt != original_prompt:
            print(f"🔧 Reframing {shot_id}: Wide -> Close Up")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(new_prompt)
            
            # מסמנים שהשוט מוכן ליצירה מחדש
            data["stills"]["status"] = "APPROVED" 
            changed_count += 1

    # שמירת הלוח
    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Updated {changed_count} prompts to be closer to camera.")
    print("👉 Now run 'python scripts/03_img_gen.py' to generate the zoomed-in versions.")

if __name__ == "__main__":
    enforce_proximity()