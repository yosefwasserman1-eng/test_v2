import os
import json
import yaml

# --- 1. הגדרת מבנה התיקיות ---
FOLDERS = [
    "assets",
    "prompts/stills",
    "prompts/video",
    "production/images",
    "production/video",
    "scripts"
]

# --- 2. תוכן הקבצים (Schemas) ---

# config.yaml - הגדרות מערכת (ללא מפתחות!)
CONFIG_CONTENT = {
    "project_name": "Tfilat HaYalda - Hybrid Workflow",
    "paths": {
        "assets": "assets/assets.yaml",
        "scenes_db": "assets/scenes_db.json",
        "shots_board": "assets/shots_board.json",
        "stills_prompts": "prompts/stills",
        "video_prompts": "prompts/video",
        "images_output": "production/images",
        "video_output": "production/video"
    },
    "models": {
        "flux": "fal-ai/flux-lora",
        "kling": "fal-ai/kling-video/v2.6/pro/image-to-video"
    },
    "settings": {
        "log_level": "INFO",
        "save_local_copies": True
    }
}

# .env - סודות בלבד
ENV_CONTENT = """ANTHROPIC_API_KEY=Put_Your_Key_Here
FAL_KEY=Put_Your_Key_Here
GEMINI_API_KEY=Put_Your_Key_Here
"""

# requirements.txt - חבילות נדרשות
REQUIREMENTS_CONTENT = """anthropic
google-generativeai
fal-client
python-dotenv
pyyaml
requests
tqdm
colorama
"""

# assets.yaml - נכסים קבועים
ASSETS_YAML_CONTENT = {
    "project_trigger": "miriN14",
    "lora_url": "https://v3b.fal.media/files/b/0a8a4202/sncujK6U_1tXMOxqLvTsB_pytorch_lora_weights.safetensors",
    "locations": {
        "FOREST_MIST": {
            "description": "Misty autumn forest path, fallen orange leaves, soft diffused morning light, atmospheric depth"
        }
    },
    "wardrobe": {
        "WINTER_CHIC": {
            "description": "Cream turtleneck, Blue hoodie jacket, Black pleated leather skirt, modest fashion"
        }
    }
}

# scenes_db.json - הקשר סצנתי
SCENES_DB_CONTENT = {
    "SCENE_1": {
        "description": "EXAMPLE: Miri walking in the forest alone.",
        "location_id": "FOREST_MIST",
        "wardrobe_id": "WINTER_CHIC",
        "mood_keywords": ["Melancholic", "Cinematic", "Cold"]
    }
}

# shots_board.json - לוח הפקה
SHOTS_BOARD_CONTENT = {
    "SHOT_001": {
        "scene_ref": "SCENE_1",
        "duration": "5s",
        "brief": {
            "visual": "Medium shot, Miri looking back over shoulder, worried expression.",
            "motion": "Camera tracks forward slowly. Wind blows hair."
        },
        "constraints": {
            "force_face_angle": "FRONT_OR_3_4",
            "framing_limit": "KNEES_UP",
            "camera_movement_speed": "SLOW",
            "avoid_occlusion": True,
            "lighting_type": "SOFT_DIFFUSED",
            "texture_complexity": "LOW",
            "prop_position": "AWAY_FROM_FACE",
            "eye_lock": "FIXED_ON_CAMERA"
        },
        "stills": {
            "status": "PENDING",
            "prompt_file": "prompts/stills/shot_001_v1.txt",
            "image_path": "",
            "feedback": ""
        },
        "video": {
            "status": "PENDING",
            "prompt_file": "prompts/video/shot_001_vid_v1.txt",
            "video_path": "",
            "feedback": ""
        }
    }
}

# .gitignore - אבטחה
GITIGNORE_CONTENT = """
.env
__pycache__/
production/
*.mp4
*.jpg
*.png
"""

# --- 3. פונקציית הבנייה ---
def create_project_structure():
    print("🚀 Initializing Iron Dome Hybrid System (Secure Version)...")
    
    # 1. יצירת תיקיות
    for folder in FOLDERS:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Created folder: {folder}/")

    # 2. יצירת קבצים
    files_to_create = [
        ("config.yaml", CONFIG_CONTENT, "yaml"),
        (".env", ENV_CONTENT, "text"),
        ("requirements.txt", REQUIREMENTS_CONTENT, "text"),
        ("assets/assets.yaml", ASSETS_YAML_CONTENT, "yaml"),
        ("assets/scenes_db.json", SCENES_DB_CONTENT, "json"),
        ("assets/shots_board.json", SHOTS_BOARD_CONTENT, "json")
    ]

    for path, content, ftype in files_to_create:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                if ftype == "json":
                    json.dump(content, f, indent=4, ensure_ascii=False)
                elif ftype == "yaml":
                    yaml.dump(content, f, allow_unicode=True, sort_keys=False)
                else: # text
                    f.write(content)
            print(f"✅ Created file: {path}")
        else:
            print(f"⚠️ File exists (skipped): {path}")

    # 3. יצירת gitignore
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w", encoding="utf-8") as f:
            f.write(GITIGNORE_CONTENT)
        print("✅ Created .gitignore")

    print("\n🎉 Setup Complete! Next steps:")
    print("1. Open '.env' and paste your REAL API KEYS.")
    print("2. Run installation: pip install -r requirements.txt")
    print("3. Tell the AI the story summary.")

if __name__ == "__main__":
    create_project_structure()