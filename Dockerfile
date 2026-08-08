FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/
COPY config/ /app/config/

ENTRYPOINT ["python", "-m", "app"]
CMD ["serve"]
