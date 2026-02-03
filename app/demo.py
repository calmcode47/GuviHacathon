"""
Run the full app (demo UI at / and detection API at /api/voice-detection).
Use: python -m app.demo
Or:  uvicorn app.main:app --reload
"""
if __name__ == "__main__":
    import uvicorn
    from app.main import app
    uvicorn.run(app, host="0.0.0.0", port=8000)
