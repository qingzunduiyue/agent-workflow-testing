from pathlib import Path
import importlib
import os
import sys
from fastapi import Header, HTTPException
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent / 'project' / 'backend'))
module, attribute = sys.argv[1].split(':')
app = getattr(importlib.import_module(module), attribute)
token = os.environ['QA_SHUTDOWN_TOKEN']
server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=int(sys.argv[2]), log_level='warning'))

# This route exists only in this test process, never in run_project.py or the application.
@app.post('/__qa_shutdown__', include_in_schema=False)
async def stop(x_qa_shutdown: str = Header(default='')):
    if x_qa_shutdown != token:
        raise HTTPException(status_code=403)
    server.should_exit = True
    return {'stopping': True}

if __name__ == '__main__':
    server.run()
