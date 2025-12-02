import logging
import uuid
from fastapi import HTTPException
from typing import Union
from fastapi import Body,FastAPI,APIRouter
from Api.login_api import get_current_user, UserInDB
from utils.qny import qny
from fastapi import UploadFile, File, Depends
import tempfile
import os
from pydantic import BaseModel


from utils.mongo_utils import mongoUtils
from fastapi import Form,Query
import json
import time
import random
import math
from OLogger.MyLogger import myLogger
qnyRouter = APIRouter(
    prefix="/qny",
    tags=["qny"],
    responses={404: {"description": "Not found"}},
)

ROLES_COLLECTION = "roles"

@qnyRouter.post("/upload/file")
async def upload_file(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
        key = f"chatbot_uploads/{uuid.uuid4()}/{file.filename}"
        url = qny.upload_file(tmp_path, key)
        os.unlink(tmp_path)
        return {"url": url}
    except Exception as e:
        return {"error": str(e)}

@qnyRouter.post("/create/role")
async def create_role(
        role_title: str = Form(...),
        role_description: str = Form(...),
        model_type: str = Form(...),
        role_prompt: str = Form(...),
        status: str = Form(...),
        other: str = Form(None),  # JSON string for other
        file: UploadFile = File(...),
        current_user: UserInDB = Depends(get_current_user)
    ):
    try:
        req_dict = {
            "role_title": role_title,
            "role_description": role_description,
            "model_type": model_type,
            "role_prompt": role_prompt,
            "status": status,
            "other": json.loads(other) if other else {}
        }
        #myLogger.info("角色生成报文"+str(req_dict))
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
        key = f"chatbot_uploads/{uuid.uuid4()}/{file.filename}"
        url = qny.upload_file(tmp_path, key)
        os.unlink(tmp_path)

        req_dict['image_url'] = url
        # Insert into MongoDB
        role_id=generate_snowflake_id()
        req_dict['role_id'] = role_id
        req_dict['user_id'] = current_user.user_id
        inserted_id = mongoUtils.insert_one(ROLES_COLLECTION, req_dict)
        #return {"id": str(inserted_id), "role": req_dict}‘
        return {"id": str(inserted_id), "role_id":role_id ,"msg": "保存成功"}
    except Exception as e:
        myLogger.error("创建角色失败报错"+str(e))
        return {"msg":"保存失败","error": str(e)}

"""
#查看所有角色
"""
@qnyRouter.post("/roles")
async def get_roles(
        page: int = Form(...),
        page_size: int = Form(...),
        status: str = Form(...),):
    filter = {"status": status}
    try:
        collection = mongoUtils.db[ROLES_COLLECTION]
        total = collection.count_documents(filter)
        roles = list(collection.find(filter).skip((page - 1) * page_size).limit(page_size))
        for role in roles:
            role['_id'] = str(role['_id'])
            role['role_id'] = str(role['role_id'])
            if 'image_url' in role:
                role['image_url'] = qny.auth.private_download_url(role['image_url'], expires=3600)
        has_more = (page * page_size) < total
        page_total = math.ceil(total / page_size) if page_size > 0 else 0
        return {"total": total, "page_num": page, "has_more": has_more, "page_total": page_total, "roles": roles}
    except Exception as e:
        return {"error": str(e)}

"""
#用户 查看用户自己创建的所有角色
"""
@qnyRouter.post("/user_roles")
async def get_roles(
        page: int = Form(...),
        page_size: int = Form(...),
        current_user: UserInDB = Depends(get_current_user)): 
    filter = {"user_id": current_user.user_id}
    try:
        collection = mongoUtils.db[ROLES_COLLECTION]
        total = collection.count_documents(filter)
        roles = list(collection.find(filter).skip((page - 1) * page_size).limit(page_size))
        for role in roles:
            role['_id'] = str(role['_id'])
            role['role_id'] = str(role['role_id'])
            if 'image_url' in role:
                role['image_url'] = qny.auth.private_download_url(role['image_url'], expires=3600)
                print("image_url",role['image_url'])
        has_more = (page * page_size) < total
        page_total = math.ceil(total / page_size) if page_size > 0 else 0
        return {"total": total, "page_num": page, "has_more": has_more, "page_total": page_total, "roles": roles}
    except Exception as e:
        return {"error": str(e)}


@qnyRouter.get("/role/{role_id}")
async def get_role_by_id(role_id: str):
    try:
        role_id=int(role_id)
        role = mongoUtils.find_one(ROLES_COLLECTION, {"role_id": role_id})
        if role:
            role['_id'] = str(role['_id'])
            role['role_id'] = str(role['role_id'])
            if 'image_url' in role:
                role['image_url'] = qny.auth.private_download_url(role['image_url'], expires=3600)
            return role
        else:
            raise HTTPException(status_code=404, detail="Role not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



"""
#更新角色 
"""
@qnyRouter.post("/update/role")
async def update_role(
        role_id: str = Form(...),
        role_title: str = Form(None),
        role_description: str = Form(None),
        model_type: str = Form(None),
        role_prompt: str = Form(None),
        status: str = Form(None),
        other: str = Form(None),
        file: UploadFile = File(None),
        current_user: UserInDB = Depends(get_current_user)
    ):
    try:
        role_id_int = int(role_id)
        existing_role = mongoUtils.find_one(ROLES_COLLECTION, {"role_id": role_id_int, "user_id": current_user.user_id})
        if not existing_role:
            raise HTTPException(status_code=404, detail="Role not found or not authorized")

        update_data = {}
        if role_title:
            update_data["role_title"] = role_title
        if role_description:
            update_data["role_description"] = role_description
        if model_type:
            update_data["model_type"] = model_type
        if role_prompt:
            update_data["role_prompt"] = role_prompt
        if status:
            update_data["status"] = status
        if other:
            update_data["other"] = json.loads(other)

        if file:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                contents = await file.read()
                tmp.write(contents)
                tmp_path = tmp.name
            key = f"chatbot_uploads/{uuid.uuid4()}/{file.filename}"
            url = qny.upload_file(tmp_path, key)
            os.unlink(tmp_path)
            update_data["image_url"] = url

        if update_data:
            mongoUtils.update_one(ROLES_COLLECTION, {"role_id": role_id_int}, update_data)

        return {"msg": "Role updated successfully"}
    except Exception as e:
        myLogger.error("更新角色失败: " + str(e))
        raise HTTPException(status_code=500, detail=str(e))
#if __name__ == "__main__":

def generate_snowflake_id(worker_id: int = 1, datacenter_id: int = 1) -> int:
    timestamp = int(time.time() * 1000)
    timestamp = timestamp - 1288834974657  # Twitter epoch
    worker_id_bits = 5
    datacenter_id_bits = 5
    sequence_bits = 12
    worker_id_shift = sequence_bits
    datacenter_id_shift = sequence_bits + worker_id_bits
    timestamp_shift = sequence_bits + worker_id_bits + datacenter_id_bits
    sequence = random.randint(0, (1 << sequence_bits) - 1)
    snowflake_id = (timestamp << timestamp_shift) | (datacenter_id << datacenter_id_shift) | (worker_id << worker_id_shift) | sequence
    return snowflake_id
