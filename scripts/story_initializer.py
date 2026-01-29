import json
import os

# נתיב לקובץ היעד
TARGET_FILE = "assets/shots_board.json"
SCENES_FILE = "assets/scenes_db.json"

# --- 1. הגדרת הסצנות (6 שלבים) ---
SCENES_DATA = {
    "SCENE_1_DEPARTURE": {
        "description": "Interior Cottage. Dark room. Embers glowing in the fireplace. Miri lights the lantern from the last dying ember. Leaves home.",
        "location_id": "MIRIS_COTTAGE_INTERIOR", # שיניתי לתוך הבית
        "wardrobe_id": "MIRI_WINTER_SHAWL",
        "mood_keywords": ["Intimate", "Warmth vs Cold", "Fireplace", "Beginning"],
        "music_segment": "Intro"
    },
    "SCENE_2_WIND": {
        "description": "Forest Path. The wind picks up. Trees swaying. The flame flickers violently. Struggle begins.",
        "location_id": "FOREST_WINDY_NIGHT",
        "wardrobe_id": "MIRI_WINTER_SHAWL",
        "mood_keywords": ["Tense", "Windy", "Dynamic Shadows", "Cold"],
        "music_segment": "Verse 1"
    },
    "SCENE_3_CRISIS": {
        "description": "Deep Forest. Heavy storm. Miri falls to the ground. The light is almost gone (dim red glow). Despair.",
        "location_id": "FOREST_STORM_GROUND",
        "wardrobe_id": "MIRI_DIRTY_MUD",
        "mood_keywords": ["Hopeless", "Dark", "Stormy", "Low Angle"],
        "music_segment": "Verse 2"
    },
    "SCENE_4_MIRACLE": {
        "description": "Same spot. Miri praying over the lantern. The flame creates a warm, magical golden sphere around her.",
        "location_id": "FOREST_STORM_GROUND",
        "wardrobe_id": "MIRI_DIRTY_MUD",
        "mood_keywords": ["Magical", "Golden Glow", "Hope", "Spiritual"],
        "music_segment": "Chorus (Prayer)"
    },
    "SCENE_5_ASCENT": {
        "description": "Mountain Path. Miri climbing up towards the synagogue. The lantern is bright and steady. She is strong.",
        "location_id": "MOUNTAIN_PATH_NIGHT",
        "wardrobe_id": "MIRI_WINTER_SHAWL",
        "mood_keywords": ["Determination", "Contrast", "Epic", "Moving Up"],
        "music_segment": "Bridge"
    },
    "SCENE_6_VICTORY": {
        "description": "Old Synagogue Entrance / Hilltop. Miri holds the light high. It illuminates the whole valley. Storm breaks.",
        "location_id": "SYNAGOGUE_ENTRANCE_NIGHT",
        "wardrobe_id": "MIRI_GLOWING",
        "mood_keywords": ["Triumph", "Bright Light", "Peace", "Majestic"],
        "music_segment": "Finale"
    }
}

# --- 2. פירוט השוטים (Beats) ---
SHOT_TEMPLATES = {
    "SCENE_1_DEPARTURE": [
        ("Close Up", "Dark screen. Focus on dying red embers in a stone fireplace.", "Static, heat shimmer."),
        ("Medium Shot", "Miri kneeling by the fireplace, holding an unlit lantern.", "Side profile."),
        ("Close Up", "Taking a small stick, lighting it from the embers.", "Hand movement."),
        ("Close Up", "Transferring the flame to the lantern wick. It ignites.", "Light flares up."),
        ("Medium Shot", "Miri's face illuminated by the new warm light. She looks worried.", "Static."),
        ("Wide Shot", "She stands up in the dark room, holding the only light.", "Slow pull back."),
        ("Close Up", "Hand reaching for the door handle. Hesitation.", "Focus on hand."),
        ("Medium Shot", "She opens the door. Wind blows in, flame flickers but stays.", "Door opening motion."),
        ("Over Shoulder", "Miri stepping out into the cold blue night.", "Tracking forward."),
        ("Wide Shot", "The cottage door closes. Miri is now a small light in the dark world.", "Static wide.")
    ],
    "SCENE_2_WIND": [
        ("Wide Shot", "Trees bending in the wind. Miri is a small light in chaos.", "Handheld shake."),
        ("Medium Shot", "Wind blows her hair across her face, she struggles.", "Tracking backward."),
        ("Close Up", "The flame flickering wildly inside the glass.", "Macro shot."),
        ("Medium Shot", "She stumbles but keeps moving.", "Low angle tracking."),
        ("Close Up", "Her hands gripping the handle tightly, knuckles white.", "Static."),
        ("Wide Shot", "Shadows of trees dancing scary shapes on the ground.", "High angle."),
        ("Medium Shot", "She shields the lantern with her whole body.", "Orbit camera."),
        ("Close Up", "Fear in her eyes as a branch breaks nearby.", "Quick zoom."),
        ("Medium Shot", "Walking against strong resistance (wind).", "Slow motion struggle."),
        ("Wide Shot", "A massive gust of wind hits her.", "Camera shake.")
    ],
    "SCENE_3_CRISIS": [
        ("Medium Shot", "Miri falls to her knees in the mud.", "Fast tilt down."),
        ("Close Up", "The lantern hits the ground (doesn't break, but dims).", "Ground level."),
        ("Wide Shot", "Total darkness surrounding her, just a faint red glow.", "High angle top down."),
        ("Close Up", "Miri's face dirty and crying, looking at the dying light.", "Static."),
        ("Medium Shot", "She curls up around the lantern, giving up.", "Slow pull back."),
        ("Close Up", "The flame is just a tiny spark now.", "Macro."),
        ("Wide Shot", "Rain/Leaves falling heavily around her.", "Atmospheric."),
        ("Medium Shot", "She buries her face in her hands.", "Static."),
        ("Close Up", "Her lips moving in silent despair.", "Focus on mouth."),
        ("Wide Shot", "She looks small and defeated.", "Extreme wide.")
    ],
    "SCENE_4_MIRACLE": [
        ("Close Up", "Miri starts whispering a prayer (Psalm).", "Static."),
        ("Medium Shot", "The spark inside the lantern suddenly stabilizes.", "Light brightens."),
        ("Close Up", "Miri's eyes open wide, seeing the light grow.", "Slow push in."),
        ("Wide Shot", "A golden warm sphere of light expands around her, pushing back the dark.", "Magical transition."),
        ("Medium Shot", "The rain seems to glow like gold around her.", "Slow motion particles."),
        ("Close Up", "A tear on her cheek shines like a diamond.", "Macro."),
        ("Medium Shot", "She lifts the lantern up, looking at it with awe.", "Low angle."),
        ("Close Up", "The flame is now strong and steady.", "Focus on flame."),
        ("Wide Shot", "She stands up slowly, bathed in golden light.", "Rising camera."),
        ("Medium Shot", "She looks forward, fear gone.", "Dolly zoom.")
    ],
    "SCENE_5_ASCENT": [
        ("Wide Shot", "Miri climbing a steep rocky path. The lantern lights the way clearly.", "Tracking side."),
        ("Medium Shot", "Her dress flowing in the wind, but she stands firm.", "Low angle."),
        ("Close Up", "Boots stepping firmly on the rocks.", "Tracking ground."),
        ("Wide Shot", "The destination (Synagogue/Hilltop) visible in distance.", "POV."),
        ("Medium Shot", "She climbs faster, almost running.", "Handheld energy."),
        ("Close Up", "Profile view, determined expression, rim lighting.", "Tracking."),
        ("Wide Shot", "Crossing a small bridge/gap.", "Crane shot."),
        ("Medium Shot", "The wind blows but the flame doesn't flicker.", "Steadycam."),
        ("Close Up", "Smiling as she sees the gate.", "Push in."),
        ("Wide Shot", "Reaching the top platform.", "Static majestic.")
    ],
    "SCENE_6_VICTORY": [
        ("Wide Shot", "Standing at the highest point. Storm clouds breaking apart.", "Epic wide."),
        ("Medium Shot", "She raises the lantern high above her head.", "Low angle hero shot."),
        ("Close Up", "The light flares into the camera lens.", "Lens flare."),
        ("Wide Shot", "The light spreads across the valley below.", "Aerial view."),
        ("Medium Shot", "Windows in the village below start lighting up in response.", "Tilt down."),
        ("Close Up", "Miri breathing in relief, closing her eyes.", "Soft focus."),
        ("Wide Shot", "The sky turns from black to deep blue (pre-dawn).", "Time lapse feel."),
        ("Medium Shot", "She hugs the lantern to her chest, smiling.", "Static."),
        ("Close Up", "Looking up at the first star/morning star.", "Looking up."),
        ("Wide Shot", "Fade out on the light of the lantern.", "Fade to black/white.")
    ]
}

def generate_full_json():
    shots_output = {}
    shot_counter = 1
    
    for scene_key, beats in SHOT_TEMPLATES.items():
        # שליפת נתוני הסצנה
        scene_info = SCENES_DATA[scene_key]
        
        for visual, desc, motion in beats:
            sid = f"SHOT_{shot_counter:03d}"
            
            # בניית האילוצים הטכניים (Technical Constraints)
            constraints = {
                "avoid_occlusion": True,
                "lighting_type": "CHIAROSCURO" # ניגודיות גבוהה של אור וצל
            }
            
            # התאמות ספציפיות לכל סצנה
            if "WIND" in scene_key:
                constraints["camera_movement_speed"] = "FAST"
                constraints["mood_color"] = "COLD_BLUE"
            elif "MIRACLE" in scene_key:
                constraints["lighting_type"] = "GOLDEN_GLOW"
                constraints["camera_movement_speed"] = "SLOW"
                constraints["eye_lock"] = "FIXED_ON_LIGHT"
            elif "VICTORY" in scene_key:
                constraints["framing_limit"] = "FULL_BODY"
            
            # וידוא שהגדרות צילום פנים (Scene 1) שונות מצילומי חוץ
            if "DEPARTURE" in scene_key:
                 constraints["lighting_type"] = "FIRE_GLOW"

            # בניית אובייקט השוט
            shot_obj = {
                "scene_ref": scene_key,
                "duration": "5s",
                "brief": {
                    "visual": f"{visual}. {desc}",
                    "motion": motion
                },
                "constraints": constraints,
                "stills": {
                    "status": "PENDING",
                    "prompt_file": f"prompts/stills/shot_{shot_counter:03d}.txt",
                    "image_path": "",
                    "version": 0
                },
                "video": {
                    "status": "PENDING",
                    "prompt_file": f"prompts/video/shot_{shot_counter:03d}.txt",
                    "video_path": "",
                    "version": 0
                }
            }
            
            shots_output[sid] = shot_obj
            shot_counter += 1

    # שמירת קובץ השוטים
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        json.dump(shots_output, f, indent=4, ensure_ascii=False)
    print(f"✅ Created {len(shots_output)} shots in {TARGET_FILE}")

    # שמירת קובץ הסצנות
    with open(SCENES_FILE, "w", encoding="utf-8") as f:
        json.dump(SCENES_DATA, f, indent=4, ensure_ascii=False)
    print(f"✅ Created scene definitions in {SCENES_FILE}")

if __name__ == "__main__":
    generate_full_json()