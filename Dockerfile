# Use lightweight Python base image
FROM python:3.12-slim

# Prevent writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies if needed (none are strictly needed, but curl/git are good practice)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to utilize Docker build cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Expose Streamlit default port (Render will override this using the PORT env var)
EXPOSE 8501

# Run the Streamlit application
# We use shell form to dynamically evaluate Render's $PORT environment variable
CMD ["sh", "-c", "streamlit run stapp_.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
