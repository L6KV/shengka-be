from typing import Union

from fastapi import Body,FastAPI,APIRouter

test_router = APIRouter(
    prefix="/test",
    tags=["test"],
    responses={404: {"description": "Not found"}},
)

@test_router.get("/")
def read_root():
    return {"Hello": "World"}


@test_router.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
