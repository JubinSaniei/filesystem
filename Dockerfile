FROM python:3.10-slim

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code files
COPY . .

# Expose the port
EXPOSE 8000

# Command to run the application with reload disabled
CMD ["python", "-m", "main", "--host=0.0.0.0", "--port=8000", "--no-access-log", "--log-level=info"]
