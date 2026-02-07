import os

def summarize_failures():
    source_root = "failures_to_analyze"
    output_file = "production/FAILURES_REPORT.txt"
    
    print(f"🕵️‍♂️ Reading text logs from: {source_root}...")
    
    if not os.path.exists(source_root):
        print(f"❌ Folder '{source_root}' not found.")
        return

    full_report = "--- COMPREHENSIVE FAILURE REPORT ---\n\n"
    count = 0

    # סריקה של כל התיקיות
    for root, dirs, files in os.walk(source_root):
        # מציאת קבצי הטקסט הרלוונטיים בתיקייה הנוכחית
        feedback_file = next((f for f in files if f == "USER_FEEDBACK.txt"), None)
        
        # חיפוש קובץ הפרומפט (מתחיל ב-shot_ ומסתיים ב-.txt)
        prompt_file = next((f for f in files if f.startswith("shot_") and f.endswith(".txt")), None)

        if feedback_file or prompt_file:
            folder_name = os.path.basename(root)
            full_report += f"========================================\n"
            full_report += f"📂 FAILURE CASE: {folder_name}\n"
            full_report += f"========================================\n"
            
            # הוספת המשוב
            if feedback_file:
                with open(os.path.join(root, feedback_file), "r", encoding="utf-8") as f:
                    full_report += f"\n--- 🗣️ USER FEEDBACK ---\n{f.read()}\n"
            
            # הוספת הפרומפט
            if prompt_file:
                with open(os.path.join(root, prompt_file), "r", encoding="utf-8") as f:
                    full_report += f"\n--- 📝 PROMPT USED ---\n{f.read()}\n"
            
            full_report += "\n\n"
            count += 1
            print(f"   ✅ Processed: {folder_name}")

    # שמירת הדוח הסופי
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_report)

    print(f"\n🎉 Done! Processed {count} failures.")
    print(f"👉 Upload this SINGLE file: {output_file}")

if __name__ == "__main__":
    summarize_failures()