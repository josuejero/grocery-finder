import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Price Service")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}