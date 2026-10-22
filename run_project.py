from pathlib import Path
import os
import sys

BACKEND = Path(__file__).resolve().parent / 'project' / 'backend'
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))
import uvicorn

if __name__ == '__main__':
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000)
