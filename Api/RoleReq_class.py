from pydantic import BaseModel
from typing import Optional


class RoleReq(BaseModel):
    role:str
    history: Optional[str] = None
    content: Optional[str] = None
    reference: Optional[str] = None