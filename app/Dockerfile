
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Default: HTTP server on 3333
EXPOSE 3333
CMD ["python", "src/server_http.py", "--host", "0.0.0.0", "--port", "3333"]
