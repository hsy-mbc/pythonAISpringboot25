from fastapi import FastAPI
from pydantic import BaseModel

from starlette.middleware.base import BaseHTTPMiddleware

import logging


app = FastAPI(
    title="MBC AI study",
    description="MBC AI study",
    version="0.0.1",
    docs_url=None,
    redoc_url=None

)   # java -> new FastAPI();

class LoggingMiddleware(BaseHTTPMiddleware):
    logging.basicConfig(level=logging.INFO) # 로그 출력
    async def dispatch(self, request, call_next):
        logging.info(f"Req: {request.method} {request.url}")
        response = await call_next(request)
        logging.info(f"Status: {response.status_code}")
        return response

app.add_middleware(LoggingMiddleware)

class Item(BaseModel):
    name: str
    description: str = None
    price: float = None
    tax: float = None

@app.get("/")
async def read_root():  # 웹 브라우저에 http://localhost:8001/ - > get 요청시 처리
    return {"Hello World"}

@app.get("/items/{item_id}") # http://localhost:8001/item/1 -> post 요청시
async def read_item(item_id:int, q: str =None):
    return {"item_id": item_id, "q": q}
    # item_id : 상품의 번호 -> 경로 매개변수
    # q : 쿼리 매개변수 (기본값 None)