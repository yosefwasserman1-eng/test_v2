FROM python:3.9-slim

WORKDIR /app

# התקנת תלויות מערכת (אם צריך)
RUN apt-get update && apt-get install -y git

# העתקת דרישות
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת כל הקבצים
COPY . .

# חשיפת הפורט
EXPOSE 8080

# הפקודה להרצת Chainlit בפורט 8080 (חובה ל-Cloud Run)
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8080", "--headless"]