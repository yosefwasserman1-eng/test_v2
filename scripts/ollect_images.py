import os
import shutil
import yaml
import json

def collect_all_latest_images():
    print("🧹 Starting Image Collection Service...")

    # טעינת הגדרות כדי לדעת איפה התיקיות
    with open("config.yaml", "r", encoding="utf-8") as f: config = yaml.safe_load(f)
    
    # תיקיית המקור (איפה שכל הבלגן)
    source_root = config["paths"]["images_output"] # בדרך כלל production/images
    
    # תיקיית היעד (התיקייה השטוחה החדשה)
    dest_dir = "production/for_upload"
    
    # מחיקה ויצירה מחדש של תיקיית היעד (כדי שלא יהיו שם זבלים ישנים)
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir)
    
    print(f"📂 Scanning: {source_root}")
    print(f"🎯 Target: {dest_dir}\n")

    count = 0
    
    # מעבר על כל התיקיות
    for root, dirs, files in os.walk(source_root):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                # מצאנו תמונה!
                full_path = os.path.join(root, file)
                
                # טריק: אנחנו רוצים לדעת מאיזה שוט זה הגיע
                # אם הקובץ הוא SHOT_001.jpg זה קל.
                # אם הוא בתוך תיקייה, ננסה לשמור על השם המקורי
                
                new_filename = file
                
                # העתקה לתיקייה השטוחה
                dest_path = os.path.join(dest_dir, new_filename)
                
                # אם כבר יש קובץ כזה (משוט אחר אולי?), נוסיף לו מספר
                if os.path.exists(dest_path):
                    name, ext = os.path.splitext(new_filename)
                    dest_path = os.path.join(dest_dir, f"{name}_duplicate_{count}{ext}")
                
                shutil.copy2(full_path, dest_path)
                print(f"✅ Collected: {new_filename}")
                count += 1

    print(f"\n🎉 Done! {count} images are waiting for you in:")
    print(f"👉 {os.path.abspath(dest_dir)}")
    print("You can now drag & drop files from this folder to Gemini.")

if __name__ == "__main__":
    collect_all_latest_images()