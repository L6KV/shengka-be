from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from Api.login_api import usersRouter
from Api.api_test import test_router
from Api.qny_api import qnyRouter
from Api.deepseek_api import dpRouter
import uvicorn


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usersRouter)
app.include_router(test_router)
app.include_router(qnyRouter)
app.include_router(dpRouter)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=12345)