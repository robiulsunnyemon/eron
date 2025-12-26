# ---- Base image ----
FROM python:3.11-slim

# ---- Working directory ----
WORKDIR /app

# ---- all copy ----
COPY . .

# ---- install Poetry ----
RUN pip install --no-cache-dir poetry

# ---- dependencies install (--no-root ) ----
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# ---- PYTHONPATH ----
ENV PYTHONPATH=/app/src:$PYTHONPATH

# ---- Port ----
EXPOSE 8000

# ---- Run the app ----
CMD ["uvicorn", "eron.main:app", "--host", "0.0.0.0", "--port", "8000"]