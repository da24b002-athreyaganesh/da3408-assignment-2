# Question 1, Part 2 -- MULTI-STAGE build.
# Stage 1 (deps)    : builds a clean virtualenv containing ONLY runtime deps.
# Stage 2 (trainer) : reuses that venv + pandas + the CSV to produce model.joblib.
# Stage 3 (runtime) : slim base; receives only the clean venv, the model and main.py.

# --- Stage 1: runtime dependency wheels ------------------------------------
FROM python:3.11 AS deps
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# --- Stage 2: train the model (discarded after the build) ------------------
FROM deps AS trainer
WORKDIR /build
# pandas is installed into this throwaway stage only.
COPY requirements-train.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements-train.txt
COPY spam_dataset.csv app/train.py ./
RUN /opt/venv/bin/python train.py --data spam_dataset.csv --out /build/model.joblib

# --- Stage 3: minimal runtime ----------------------------------------------
FROM python:3.11-slim AS runtime
ARG APP_VERSION=dev
WORKDIR /app

# Clean venv from stage 1 -- NOT the pandas-polluted one from stage 2.
COPY --from=deps /opt/venv /opt/venv
# Only the 4 KB trained artifact crosses over from the trainer.
COPY --from=trainer /build/model.joblib /app/model.joblib
COPY app/main.py /app/main.py

ENV APP_VERSION=${APP_VERSION} \
    PATH="/opt/venv/bin:$PATH" \
    MODEL_PATH=/app/model.joblib \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
