from fastapi import FastAPI, UploadFile, File
from typing import List, Annotated, Sequence

app = FastAPI(openapi_version="3.0.2")

@app.post("/upload1")
async def upload1(files: List[UploadFile] = File(...)):
    return {"len": len(files)}

@app.post("/upload2")
async def upload2(files: Sequence[UploadFile] = File(...)):
    return {"len": len(files)}

import json
print(json.dumps(app.openapi()['components']['schemas'], indent=2))
