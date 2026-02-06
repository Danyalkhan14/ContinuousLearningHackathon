# ── Stage 1: Build the React/Vite frontend ──────────────────────────
FROM node:22-alpine AS frontend

WORKDIR /build
COPY UI/package.json UI/package-lock.json ./
RUN npm ci

COPY UI/ ./
# Empty string → fetch("/api/...") uses the same origin as the page
ENV VITE_AGENT_API_URL=""
RUN npm run build          # outputs to /build/dist


# ── Stage 2: Python backend + serve static frontend ─────────────────
FROM python:3.12-slim

# System deps for pymupdf (MuPDF) and general use
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmupdf-dev gcc g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY Agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent source code
COPY Agent/ ./

# Copy the built frontend into a static directory
COPY --from=frontend /build/dist ./static

# Expose the port Render expects
EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
