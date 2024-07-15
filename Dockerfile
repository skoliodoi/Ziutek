FROM python:3.11-slim

WORKDIR /app

# COPY .env /app/.env  

COPY ziutek-key.json /app/ziutek-key.json  

COPY . /app

ENV PYTHONUNBUFFERED=1

ENV GOOGLE_APPLICATION_CREDENTIALS=/app/ziutek-key.json

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3969

CMD ["python", "app.py"]
