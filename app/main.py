"""Spam-detection REST API with a Redis look-aside cache.

Contract:
  POST /predict  {"text": "..."}  ->  {"label": "spam"} | {"label": "ham"}
  GET  /healthz                   ->  200 once the model is loaded

Cache behaviour (Q2):
  key  = "spam:" + sha256(text)
  MISS -> run the model, SETEX the label under CACHE_TTL_SECONDS, return it
  HIT  -> return the stored label without touching the model

Redis is optional on purpose. If it is unreachable the API still serves
predictions, just uncached. That is what lets this same image run under
Kubernetes in Q4 with no Redis alongside it.
"""
import hashlib
import os
import time
from contextlib import asynccontextmanager

import joblib
import redis
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

MODEL_PATH = os.getenv("MODEL_PATH", "/app/model.joblib")
REDIS_HOST = os.getenv("REDIS_HOST", "cache")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
APP_VERSION = os.getenv("APP_VERSION", "dev")

state: dict = {"model": None, "cache": None}


def cache_key(text: str) -> str:
    return "spam:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["model"] = joblib.load(MODEL_PATH)
    print(f"Loaded model from {MODEL_PATH}", flush=True)
    try:
        client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT,
            socket_timeout=1, socket_connect_timeout=1,
            decode_responses=True,
        )
        client.ping()
        state["cache"] = client
        print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT} "
              f"(TTL {CACHE_TTL_SECONDS}s)", flush=True)
    except Exception as exc:  # includes DNS failure when no cache exists
        state["cache"] = None
        print(f"Redis unavailable ({exc}); serving without cache", flush=True)
    yield
    state["model"] = None
    state["cache"] = None


app = FastAPI(title="Spam Detection API", lifespan=lifespan)


class PredictRequest(BaseModel):
    text: str


class PredictResponse(BaseModel):
    label: str


@app.get("/healthz")
def healthz():
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ok", "version": APP_VERSION,
            "cache": state["cache"] is not None}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, response: Response):
    model = state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    cache = state["cache"]
    key = cache_key(req.text)
    started = time.perf_counter()

    if cache is not None:
        try:
            hit = cache.get(key)
        except redis.RedisError:
            hit = None
        if hit is not None:
            elapsed = (time.perf_counter() - started) * 1000
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Elapsed-MS"] = f"{elapsed:.3f}"
            print(f"HIT   {elapsed:7.3f} ms  {key[:18]}", flush=True)
            return {"label": hit}

    label = str(model.predict([req.text])[0])
    if cache is not None:
        try:
            cache.setex(key, CACHE_TTL_SECONDS, label)
        except redis.RedisError:
            pass

    elapsed = (time.perf_counter() - started) * 1000
    response.headers["X-Cache"] = "MISS" if cache is not None else "BYPASS"
    response.headers["X-Elapsed-MS"] = f"{elapsed:.3f}"
    print(f"MISS  {elapsed:7.3f} ms  {key[:18]}", flush=True)
    return {"label": label}
