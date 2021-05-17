import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def test():
    return {"message": "Hello World"} 

if __name__ == "__main__":
    uvicorn.run(app, port=8001, host="0.0.0.0")