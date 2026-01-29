import os
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

# המודל הנבחר (החזק ביותר נכון ל-2026/היום)
MODEL_NAME = "claude-3-5-sonnet-20241022" 

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