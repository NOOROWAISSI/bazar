FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
RUN useradd --create-home app && mkdir /data && chown app:app /data
USER app
CMD ["waitress-serve", "--listen=0.0.0.0:5000", "frontend:app"]
