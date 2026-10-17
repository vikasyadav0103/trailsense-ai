# Build the React frontend first.
FROM node:22-alpine AS frontend-build
WORKDIR /workspace/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Run FastAPI and serve the compiled React app from the same container.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8000
WORKDIR /app
COPY ai-service/requirements.txt /app/ai-service/requirements.txt
RUN pip install --no-cache-dir -r /app/ai-service/requirements.txt
COPY ai-service/app /app/ai-service/app
COPY --from=frontend-build /workspace/frontend/dist /app/frontend/dist
WORKDIR /app/ai-service
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
