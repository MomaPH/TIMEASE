"""Entry point — start the TIMEASE FastAPI server."""
from dotenv import load_dotenv
load_dotenv()

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    uvicorn.run(
        "timease.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
