#!/usr/bin/env python3
"""Launch the AI Readiness Simulation Game server."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uvicorn
from server.config import settings
uvicorn.run("server.main:app", host=settings.host, port=settings.port, reload=False)
