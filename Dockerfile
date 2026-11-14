# Reference configuration authored by Noor (origin/noor, commit 1b874a6).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt waitress==3.0.2
COPY catalog.py frontend.py order.py ./
RUN useradd --create-home app && mkdir -p /app/data /data && chown -R app:app /app/data /data
USER app
CMD ["waitress-serve", "--listen=0.0.0.0:5000", "frontend:app"]
