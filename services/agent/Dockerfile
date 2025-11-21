# Use 3.11 or 3.12. 3.14 is too new for reliable ML wheels right now.
FROM python:3.11-slim

WORKDIR /app

# Install system deps for Playwright and compiling
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy code
COPY . .

# Run FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
