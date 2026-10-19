FROM python:3.11-slim

WORKDIR /app

# Install CPU-only PyTorch first, which is much smaller than the default build.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY static/ ./static/
COPY eval/ ./eval/
COPY data/chroma/ ./data/chroma/
COPY data/chunks.json ./data/chunks.json
COPY data/recipes.json ./data/recipes.json
COPY data/items.json ./data/items.json

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
