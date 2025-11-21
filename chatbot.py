from fastapi import Depends, FastAPI
from chroma_connection import get_chroma_collection

app = FastAPI()

@app.post("/api_route/")
async def use_chroma(collection=Depends(get_chroma_collection)):
    return


