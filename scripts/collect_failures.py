import os
import shutil

def collect_failures_for_upload():
    # הגדרות נתיבים
    source_root = "failures_to_analyze"
    dest_dir = "production/failures_flat"
    
    print(f"🕵️‍♂️ Focusing ONLY on: {source_root}")
    
    # בדיקה שהתיקייה בכלל קיימת
    if not os.path.exists(source_root):
        print(f"❌ Error: Could not find folder '{source_root}'")
        return

    # ניקוי תיקיית היעד
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir)
    
    count = 0
    print(f"🚀 Flattening files to: {dest_dir} ...\n")

    # סריקה
    for root, dirs, files in os.walk(source_root):
        for file in files:
            # מעניינים אותנו תמונות וקבצי טקסט (כדי שנראה גם את התמונה וגם את הלוג)
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.txt')):
                
                src_path = os.path.join(root, file)
                
                # כדי למנוע דריסה של קבצים עם אותו שם (כמו shot.txt),
                # נוסיף לשם הקובץ את שם התיקייה שממנה הוא הגיע (שהוא בדרך כלל ה-TIMESTAMP)
                parent_folder = os.path.basename(root)
                new_filename = f"{parent_folder}_{file}"
                
                dest_path = os.path.join(dest_dir, new_filename)
                
                shutil.copy2(src_path, dest_path)
                print(f"   📄 Copied: {new_filename}")
                count += 1

    print(f"\n✅ Done! {count} failure files are ready.")
    print(f"👉 Go to folder: {dest_dir}")
    print("   Select all files there -> Drag & Drop to Gemini.")

if __name__ == "__main__":
    collect_failures_for_upload()