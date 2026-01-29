import yaml
import os
from claude_client import client, MODEL_NAME

ASSETS_FILE = "assets/assets.yaml"

def refine_assets():
    if not os.path.exists(ASSETS_FILE):
        print("❌ assets.yaml not found! Please create it first.")
        return

    with open(ASSETS_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    print("🎨 Starting Asset Refinement (Polishing the source of truth)...")

    # פונקציית עזר לשליחה לקלוד
    def get_optimized_description(category, item_id, current_desc):
        prompt = f"""
        You are an expert Visual Costume & Set Designer for 1850s period films.
        Your task: Rewrite the description below to be a PERFECT image generation prompt for Flux.1.
        
        INPUT ({category}): "{current_desc}"
        
        RULES:
        1. Keep it visual and factual (materials, textures, colors, lighting interaction).
        2. Period accurate (19th century shtetl/village aesthetic).
        3. NO poetic fluff ("a sense of wonder"). ONLY visual facts.
        4. Max 40 words.
        5. Output ONLY the new description.
        """
        
        try:
            print(f"   ✨ Polishing {item_id}...")
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=100,
                system=prompt,
                messages=[{"role": "user", "content": "Refine this description."}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"   ❌ Error on {item_id}: {e}")
            return current_desc

    # מעבר על כל התלבושות
    if "wardrobe" in data:
        print("\n👗 Refining Wardrobe...")
        for w_id, w_data in data["wardrobe"].items():
            # בודק אם כבר יש דגל 'optimized', אם לא - משפר
            if not w_data.get("is_optimized"):
                new_desc = get_optimized_description("Wardrobe", w_id, w_data["description"])
                data["wardrobe"][w_id]["description"] = new_desc
                data["wardrobe"][w_id]["is_optimized"] = True # מסמן שזה טופל

    # מעבר על כל הלוקיישנים
    if "locations" in data:
        print("\n🏰 Refining Locations...")
        for l_id, l_data in data["locations"].items():
            if not l_data.get("is_optimized"):
                new_desc = get_optimized_description("Location", l_id, l_data["description"])
                data["locations"][l_id]["description"] = new_desc
                data["locations"][l_id]["is_optimized"] = True

    # שמירה חזרה לקובץ
    with open(ASSETS_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    
    print("\n✅ Assets optimized and saved to assets.yaml!")
    print("   Now Claude will use EXACTLY these descriptions for every shot.")

if __name__ == "__main__":
    refine_assets()