from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from Api.login_api import usersRouter
from Api.api_test import test_router
from Api.qny_api import qnyRouter
from Api.deepseek_api import dpRouter

#from routers.items import itemsRouter
import uvicorn
from config.config_read import configReader

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from Api.login_api import SECRET_KEY, ALGORITHM
from fastapi.middleware.cors import CORSMiddleware

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

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    excluded_paths = ["/users/register", "/users/token", "/refresh"]
    if any(request.url.path.startswith(path) for path in excluded_paths):
        return await call_next(request)
    
    token = request.headers.get("Authorization")
    if not token:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Missing token"})
    
    try:
        scheme, _, token_value = token.partition(" ")
        if scheme.lower() != "bearer":
            raise ValueError("Invalid token scheme")
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise JWTError
    except (JWTError, ValueError):
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Invalid or expired token"})
    
    return await call_next(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=12345)