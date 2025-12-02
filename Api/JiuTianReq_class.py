from pydantic import BaseModel


class RoleReq(BaseModel):
    role:str
    history:str|None=None
    content :str|None=None
    reference :str|None=None