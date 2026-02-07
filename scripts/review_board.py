import streamlit as st
import json
import yaml
import os

# הגדרת עמוד
st.set_page_config(layout="wide", page_title="Director's Cut Board")

def load_data():
    with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
    with open(config["paths"]["shots_board"], "r", encoding="utf-8") as f: shots = json.load(f)
    return config, shots

def save_shots(shots, config):
    with open(config["paths"]["shots_board"], "w", encoding="utf-8") as f:
        json.dump(shots, f, indent=4, ensure_ascii=False)

config, shots = load_data()

# --- סטטיסטיקות בצד (Sidebar) ---
total = len(shots)
# ספירת סטטוסים
img_ready = len([s for s in shots.values() if s["stills"].get("status") == "IMAGE_READY"])
approved = len([s for s in shots.values() if s["stills"].get("status") == "APPROVED"])
rejected = len([s for s in shots.values() if s["stills"].get("status") == "REJECTED"])
waiting_gen = len([s for s in shots.values() if s["stills"].get("status") == "PROMPT_READY"])

st.sidebar.title("📊 Production Status")
st.sidebar.progress(approved / total if total > 0 else 0)
st.sidebar.markdown(f"""
* **Total Shots:** {total}
* 🟢 **Approved:** {approved}
* 🟡 **To Review:** {img_ready}
* ⚪ **Waiting Generation:** {waiting_gen}
* 🔴 **Rejected (Needs Repair):** {rejected}
""")

if waiting_gen > 0:
    st.sidebar.warning(f"⚠️ {waiting_gen} shots hold no image.\nRun `python scripts/03_img_gen.py`")

# --- גוף ראשי ---
st.title("🎬 Director's Review Board")

mode = st.radio("Select Mode:", ["👀 Review Queue", "✅ Approved Gallery", "📋 All Data"], horizontal=True)

if mode == "👀 Review Queue":
    to_review = [sid for sid, s in shots.items() if s["stills"].get("status") == "IMAGE_READY"]
    
    if not to_review:
        st.success("🎉 הכל נקי! אין תמונות שמחכות לביקורת.")
        if waiting_gen > 0:
            st.info(f"אבל... יש עוד {waiting_gen} שוטים שצריך לייצר. תריץ את סקריפט 03.")
    else:
        # לוקחים את הראשון בתור
        shot_id = to_review[0]
        shot = shots[shot_id]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            img_path = shot["stills"].get("image_path")
            if img_path and os.path.exists(img_path):
                st.image(img_path, caption=f"Current View: {shot_id}", use_column_width=True)
            else:
                st.error(f"Image File Missing: {img_path}")
        
        with col2:
            st.subheader(f"Shot: {shot_id}")
            st.caption(f"Scene: {shot.get('scene_id')}")
            
            # הצגת הפרומפט
            prompt_file = shot["stills"].get("prompt_file")
            if prompt_file and os.path.exists(prompt_file):
                with open(prompt_file, "r", encoding="utf-8") as f:
                    st.text_area("Prompt used:", f.read(), height=150)
            
            with st.form("decision_form"):
                st.write("### Director's Decision")
                status = st.radio("Action:", ["Approve", "Reject (Requires Fix)"])
                notes = st.text_input("Feedback / Fix Instructions:")
                
                if st.form_submit_button("Submit Decision"):
                    if status == "Approve":
                        shots[shot_id]["stills"]["status"] = "APPROVED"
                        st.balloons()
                    else:
                        shots[shot_id]["stills"]["status"] = "REJECTED"
                        shots[shot_id]["stills"]["inspector_feedback"] = notes
                    
                    save_shots(shots, config)
                    st.rerun()

elif mode == "✅ Approved Gallery":
    approved_shots = [sid for sid, s in shots.items() if s["stills"].get("status") == "APPROVED"]
    if not approved_shots:
        st.write("No approved shots yet.")
    else:
        # תצוגת גריד
        cols = st.columns(3)
        for i, sid in enumerate(approved_shots):
            img = shots[sid]["stills"].get("image_path")
            if img and os.path.exists(img):
                cols[i % 3].image(img, caption=sid)

elif mode == "📋 All Data":
    st.json(shots)