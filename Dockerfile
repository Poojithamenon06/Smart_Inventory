# Stage 1: build the React app
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend that also serves the built app
FROM python:3.13-slim
WORKDIR /app
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt
COPY backend/ backend/
COPY ml/ ml/
COPY demo/ demo/
COPY --from=web /web/dist frontend/dist
CMD ["sh", "-c", "mkdir -p data && cp demo/inventory.db data/inventory.db && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]