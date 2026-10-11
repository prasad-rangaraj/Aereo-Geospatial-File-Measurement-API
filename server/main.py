"""Convenience root entrypoint allowing: uvicorn main:app --reload directly from backend/"""
from app.main import app

__all__ = ["app"]
