# Dockerfile unificado - Backend + Frontend
# Stage 1: Build do Frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copiar package.json e instalar dependências
COPY frontend/package*.json ./
RUN npm ci

# Copiar código do frontend
COPY frontend/ .

# Build do frontend (o VITE_API_URL será relativo, mesmo domínio)
ENV VITE_API_URL=/api/v1
RUN npm run build

# Stage 2: Backend Python com Frontend
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do backend
COPY backend/ .

# Copiar frontend buildado para pasta static
COPY --from=frontend-builder /frontend/dist ./static

# Expor porta
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
