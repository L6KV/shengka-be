from typing import Union
from OLogger.MyLogger import myLogger
from fastapi import FastAPI,Request,Response
from pydantic import BaseModel
import uvicorn

#DTO Req 和 Resp
from RoleReq_class import RoleReq
from LLM_utils.LLM_Connection import my_deepseek
app = FastAPI()


'''****************************两个示例接口********************************'''
@app.get('/ChatSingle')
async def read_results(request: Request):
    #results = await some_library()
    client_host = request.client.host
    headers = dict(request.headers)
    print(client_host)
    print(headers)
    results="大模型单向输出"
    myLogger.info(results)
    return results

@app.post('/ChatSingle2')
async def read_results(request: Request):
    #results = await some_library()
    client_host = request.client.host
    headers = dict(request.headers)
    print(client_host)
    print(headers)
    results="大模型单向输出"
    myLogger.info(results)
    return results


'''**********************deepseek api调用接口 chat******************************'''
@app.post('/ChatDeepseek')
async def Chat_Deepseek(roleReq: RoleReq):
    #results = await some_library()
    # client_host = roleReq.client.host
    # headers = dict(roleReq.headers)
    global results
    try:
        results= await my_deepseek.dp_chat(roleReq)
    except Exception as e:
        results = {"code":500,"message":str(e)}
        myLogger.error(e)
    myLogger.info(results)
    return results



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=12345)