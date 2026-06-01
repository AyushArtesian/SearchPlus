release: python -c "from src.storage import init_db; init_db()"
web: uvicorn main:app --host 0.0.0.0 --port $PORT
