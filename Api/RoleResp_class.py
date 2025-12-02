from pydantic import BaseModel
from typing import Optional


class RoleResp(BaseModel):
    content: Optional[str] = None
