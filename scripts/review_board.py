import streamlit as st
import json
import yaml
import os
import shutil
import datetime

# --- הגדרות וכותרות ---
st.set_page_config(page_title="Production Review", layout="wide")
st.title("🎬 Production Review Board")

# --- טעינת דאטה ---
try:
    with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
    SHOTS_FILE = config["paths"]["shots_board"]
    with open(SHOTS_FILE, "r", encoding="utf-8") as f: shots_data = json.load(f)
except Exception as e:
    st.error(f"Error loading config or data: {e}")
    st.stop()

# --- פונקציות עזר ---
def save_db():
    with open(SHOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(shots_data, f, indent=4, ensure_ascii=False)

def package_failure(shot_id, feedback_text, stage):
    """
    אורז את כל הנכסים של השוט הכושל לתיקייה אחת כדי שיהיה קל להעלות לקלוד/ג'ימיני לניתוח
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"FAILURE_{shot_id}_{stage}_{timestamp}"
    base_path = "failures_to_analyze"
    target_dir = os.path.join(base_path, folder_name)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    shot = shots_data[shot_id]
    files_copied = []

    # 1. העתקת התמונה (תמיד רלוונטי)
    img_path = shot["stills"].get("image_path")
    if img_path and os.path.exists(img_path):
        shutil.copy(img_path, target_dir)
        files_copied.append("Image")

    # 2. העתקת הוידאו (אם אנחנו בשלב וידאו)
    vid_path = shot["video"].get("video_path")
    if stage == "VIDEO" and vid_path and os.path.exists(vid_path):
        shutil.copy(vid_path, target_dir)
        files_copied.append("Video")

    # 3. העתקת הפרומפטים
    # סטילס
    stills_prompt_path = shot["stills"].get("prompt_file")
    if stills_prompt_path and os.path.exists(stills_prompt_path):
        shutil.copy(stills_prompt_path, target_dir)
    
    # וידאו
    if stage == "VIDEO":
        vid_prompt_path = shot["video"].get("prompt_file")
        if vid_prompt_path and os.path.exists(vid_prompt_path):
            shutil.copy(vid_prompt_path, target_dir)

    # 4. יצירת קובץ הדיווח (התלונה שלך)
    report_path = os.path.join(target_dir, "USER_FEEDBACK.txt")
    report_content = f"""
    SHOT ID: {shot_id}
    STAGE: {stage}
    -------------------
    USER COMPLAINT:
    {feedback_text}
    -------------------
    METADATA:
    Scene: {shot.get('scene_ref')}
    Duration: {shot.get('duration')}
    Constraints: {json.dumps(shot.get('constraints', {}), indent=2)}
    """
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    return target_dir

# --- לוגיקה ראשית ---

# מציאת שוטים שממתינים לסקירה
# לוגיקה: אם יש תמונה והסטטוס הוא IMAGE_READY -> סקירת סטילס
# לוגיקה: אם יש וידאו והסטטוס הוא VIDEO_READY -> סקירת וידאו

pending_shots = []
for sid, data in shots_data.items():
    stills_stat = data["stills"]["status"]
    video_stat = data["video"]["status"]
    
    if stills_stat == "IMAGE_READY":
        pending_shots.append({"id": sid, "stage": "STILLS", "data": data})
    elif video_stat == "VIDEO_READY": # או סטטוס אחר שמסמן וידאו מוכן
        pending_shots.append({"id": sid, "stage": "VIDEO", "data": data})

# --- UI ---
st.sidebar.header(f"Pending Review ({len(pending_shots)})")
selected_shot_wrapper = None

if pending_shots:
    # בחירה מרשימה
    shot_ids = [f"{s['id']} ({s['stage']})" for s in pending_shots]
    selection = st.sidebar.radio("Select Shot:", shot_ids)
    
    # שליפת המידע הנבחר
    selected_id = selection.split(" ")[0]
    selected_shot_wrapper = next(s for s in pending_shots if s['id'] == selected_id)
    
    shot_id = selected_shot_wrapper['id']
    stage = selected_shot_wrapper['stage']
    shot = selected_shot_wrapper['data']

    # --- תצוגה ראשית ---
    st.header(f"Reviewing: {shot_id}")
    st.info(f"Visual Brief: {shot.get('brief', {}).get('visual', 'N/A')}")
    
    col_media, col_ctrl = st.columns([2, 1])
    
    with col_media:
        # הצגת המדיה הרלוונטית
        if stage == "STILLS":
            img_path = shot["stills"]["image_path"]
            if os.path.exists(img_path):
                st.image(img_path, caption=f"Stills V{shot['stills'].get('version')}", use_container_width=True)
            else:
                st.error(f"File not found: {img_path}")
                
        elif stage == "VIDEO":
            vid_path = shot["video"]["video_path"]
            if os.path.exists(vid_path):
                st.video(vid_path)
            else:
                st.error(f"File not found: {vid_path}")

    with col_ctrl:
        st.subheader("Decision")
        
        # טופס אישור
        if st.button("✅ APPROVE", type="primary", use_container_width=True):
            if stage == "STILLS":
                shot["stills"]["status"] = "APPROVED"
                # טריגר אוטומטי לוידאו: פותח את הנעילה
                shot["video"]["status"] = "READY_FOR_PROMPT" 
            elif stage == "VIDEO":
                shot["video"]["status"] = "DONE"
            
            save_db()
            st.success("Approved! Moving to next...")
            st.rerun()

        st.divider()
        
        # טופס דחייה
        with st.form(key="reject_form"):
            st.write("❌ REJECT & ANALYZE")
            feedback = st.text_area("What is wrong?", placeholder="Eyes are distorted / Camera moves too fast...")
            
            if st.form_submit_button("Reject & Package"):
                if feedback:
                    # 1. יצירת חבילת דיבאג
                    folder = package_failure(shot_id, feedback, stage)
                    
                    # 2. עדכון סטטוס
                    if stage == "STILLS":
                        shot["stills"]["status"] = "REJECTED"
                        shot["stills"]["feedback"] = feedback
                    elif stage == "VIDEO":
                        shot["video"]["status"] = "REJECTED"
                        shot["video"]["feedback"] = feedback
                    
                    save_db()
                    st.success(f"Packaged for analysis in: {folder}")
                    st.warning("Status set to REJECTED")
                else:
                    st.error("Please describe the issue.")

else:
    st.success("🎉 All caught up! No shots pending review.")
    st.balloons()