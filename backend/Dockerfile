FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for any compiled python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8080 for Google Cloud Run
EXPOSE 8080

# Command to run the application
CMD ["sh", "-c", "uvicorn pdfreader:app --host 0.0.0.0 --port ${PORT:-8080}"]
