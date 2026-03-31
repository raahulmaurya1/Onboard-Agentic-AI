from fastapi import FastAPI, UploadFile, File
from typing import List, Annotated

app = FastAPI()

@app.post("/upload1")
async def upload1(files: List[UploadFile] = File(...)):
    return {"len": len(files)}

@app.post("/upload2")
async def upload2(files: list[UploadFile] = File(...)):
    return {"len": len(files)}

@app.post("/upload3")
async def upload3(files: list[bytes] = File(...)):
    return {"len": len(files)}

print("Script written.")
