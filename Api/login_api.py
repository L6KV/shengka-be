from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
import uvicorn
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
import secrets
from utils.mongo_utils import MongoUtils
import hashlib  # 用于真实密码哈希
import time
import random
from fastapi import Form,Query

def generate_snowflake_id():
    timestamp = int(time.time() * 1000)
    worker_id = random.randint(0, 31)
    process_id = random.randint(0, 31)
    sequence = random.randint(0, 4095)
    snowflake_id = (timestamp << 22) | (worker_id << 17) | (process_id << 12) | sequence
    return str(snowflake_id)

app = FastAPI()
usersRouter = APIRouter()

SECRET_KEY = "your-fixed-secret-key"  # 使用固定密钥，避免重启时变化
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_SECRET = "your-fixed-refresh-secret-key"  # 固定 refresh 密钥

# MongoDB 配置
mongo = MongoUtils(uri="mongodb://localhost:27017/", db_name="chatbot_db")
USER_COLLECTION = "users"

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_access_token(username: str):
    payload = {
        "username": username,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "sub": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def generate_refresh_token(username: str):
    payload = {
        "username": username,
        "sub": "refresh",
    }
    return jwt.encode(payload, REFRESH_SECRET, algorithm=ALGORITHM)

def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, REFRESH_SECRET, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    user_id: str
    hashed_password: str

def get_user(username: str):
    user_data = mongo.find_one(USER_COLLECTION, {"username": username})
    if user_data:
        if 'user_id' not in user_data:
            user_data['user_id'] = str(user_data['_id'])
        else:
            user_data['user_id'] = str(user_data['user_id'])
        return UserInDB(**user_data)
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username=username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@usersRouter.post("/users/register")
async def register_user(form_data: OAuth2PasswordRequestForm = Depends()):
    existing_user = get_user(form_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = hash_password(form_data.password)
    user_id = generate_snowflake_id()
    user_data = {
        "user_id": user_id,
        "username": form_data.username,
        "hashed_password": hashed_password,
        "disabled": False
    }
    mongo.insert_one(USER_COLLECTION, user_data)
    return {"detail": "User registered successfully"}

@usersRouter.post("/users/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if hash_password(form_data.password) != user.hashed_password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = generate_refresh_token(user.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@usersRouter.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@usersRouter.post("/refresh")
async def refresh_token(refresh_token: str = Form(...),):
    try:
        payload = jwt.decode(refresh_token, REFRESH_SECRET, algorithms=[ALGORITHM])
        if payload["sub"] != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        username = payload["username"]
        access_token = generate_access_token(username)
        return {"access_token": access_token}
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate refresh token")



@usersRouter.get("/users/protected-endpoint")
async def protected_route(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Hello, {current_user.username}! This is a protected endpoint."}

@usersRouter.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")
    result = mongo.delete_one(USER_COLLECTION, {"user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"detail": "User deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=12345)






