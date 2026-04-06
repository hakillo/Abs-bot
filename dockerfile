FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y build-essential git curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app

# Use Render’s $PORT environment variable
ENV PORT=10000

# Expose the port
EXPOSE $PORT

# Run both FastAPI and Streamlit (for demo purposes)
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT & streamlit run ui.py --server.port $PORT --server.address 0.0.0.0"]