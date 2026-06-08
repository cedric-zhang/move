"""Tognix-Move — Zabbix → Tognix 迁移工具
FastAPI 入口""" 
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.config import APP_CONFIG

app = FastAPI(title='Tognix-Move', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '0.1.0'}

static_dir = Path(__file__).parent.parent / 'static'

@app.get('/')
def index():
    index_file = static_dir / 'index.html'
    if index_file.exists():
        return FileResponse(str(index_file))
    return {'message': 'Tognix-Move API', 'version': '0.1.0'}

if static_dir.exists():
    app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')

if __name__ == '__main__':
    uvicorn.run(app, host=APP_CONFIG['host'], port=APP_CONFIG['port'])
