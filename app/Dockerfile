FROM python:3.12-slim

WORKDIR /app

# TA-Lib ships prebuilt wheels (with the C library bundled), so no compiler is needed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Print logs immediately so `docker compose logs` is useful
ENV PYTHONUNBUFFERED=1

COPY . .

CMD ["python", "ingestion.py"]
