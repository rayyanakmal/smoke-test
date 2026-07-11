from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
async def hello():
    return {"message": "hello world"}


@app.get("/health")
async def health():
    return {"status": "ok"}
