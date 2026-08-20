FROM python:3.12-slim

WORKDIR /code

# Install dependencies in a separate layer for better cache reuse
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Run as non-root user
RUN useradd --no-create-home appuser
USER appuser

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
