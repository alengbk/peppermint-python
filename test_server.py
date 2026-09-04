#!/usr/bin/env python3
"""Simple test server for Peppermint Python API"""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Peppermint API",
    description="Test server for API testing",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"healthy": True, "service": "peppermint-python-api"}

@app.get("/api/v1/ticket/public/create")
def create_public_ticket():
    # Mock implementation for testing
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "title": "Test Ticket",
        "detail": "Created via API",
        "status": "needs_support",
        "priority": "low",
        "type": "support",
        "isComplete": False,
        "locked": False,
        "hidden": False,
        "createdAt": "2026-07-23T12:00:00"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5003, log_level="info")
