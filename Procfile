release: python -c "from src.storage import init_db; init_db()"
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
