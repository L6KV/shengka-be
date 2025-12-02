import json

from langchain.chains.question_answering.map_reduce_prompt import messages
from openai import OpenAI

from LLM_utils.config.config_read import my_read_configer

from OLogger.MyLogger import myLogger
from Api.RoleReq_class import RoleReq
from Api.RoleResp_class import RoleResp

myLogger.info(f"LLM_Connection.py loaded")

class My_deepseek:
    def __init__(self):
        self.config = my_read_configer

        self.api_dp_key = my_read_configer.get('api_dp_key')
        self.dp_base_url = my_read_configer.get('dp_base_url')
        self.dp_chat_model = my_read_configer.get('dp_chat_model')

        self.dp_reasoner_model = my_read_configer.get('dp_reasoner_model')

        myLogger.info(f"Using DeepSeek API Key: {self.api_dp_key}")
        myLogger.info(f"Using DeepSeek Base URL: {self.dp_base_url}")
        self.client = OpenAI(api_key=self.api_dp_key, base_url=self.dp_base_url)

    async def dp_chat(self, roleReq: RoleReq) -> RoleResp:
        messages = [
            #{},
            {"role": roleReq.role, "content": roleReq.content, }
        ]

        global resp_dict
        global dp_content
        roleReq=RoleResp()
        try:
            resp_dp = self.client.chat.completions.create(
                model=self.dp_reasoner_model,
                messages=messages,
                stream=False,
                temperature=1.3
            )
            myLogger.info("返回报文" + str(resp_dp))

            resp_dict =json.loads(resp_dp.model_dump_json())

        except Exception as e:
            resp_dict = dict
            myLogger.error("连接deepseek出问题")
            myLogger.error(e)

        try:
            dp_content = resp_dict.get('choices')[0].get('message').get('content')
        except Exception as e:
            dp_content="deepseek返回出现问题"
            myLogger.error("deepseek返回报文出问题")

        roleReq.content = dp_content
        return roleReq


my_deepseek_instance = None

def get_my_deepseek():
    global my_deepseek_instance
    if my_deepseek_instance is None:
        my_deepseek_instance = My_deepseek()
    return my_deepseek_instance

my_deepseek = get_my_deepseek()
