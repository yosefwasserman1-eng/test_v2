import os
import yaml
import anthropic
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# טעינת מפתחות
load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("⚠️ WARNING: ANTHROPIC_API_KEY not found in .env")

# הגדרת הלקוח
client = anthropic.Anthropic(api_key=api_key)

# --- טעינת מודל מקובץ הקונפיגורציה ---
try:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        # שליפת המודל מהקובץ, עם ברירת מחדל למקרה ששכחת לעדכן
        MODEL_NAME = config.get("models", {}).get("claude", "claude-3-5-sonnet-20241022")
except Exception as e:
    print(f"⚠️ Warning: Could not load config.yaml ({e}). Using default model.")
    MODEL_NAME = "claude-3-5-sonnet-20241022"

print(f"🧠 Claude Client initialized with model: {MODEL_NAME}")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_claude_response(system_prompt, user_prompt):
    """
    פונקציה עוטפת ששולחת בקשה לקלוד עם ניהול שגיאות אוטומטי (Retry)
    """
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text
    except Exception as e:
        print(f"❌ Claude API Error: {e}")
        raise e