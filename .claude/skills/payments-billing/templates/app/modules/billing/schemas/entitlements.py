from pydantic import BaseModel


class EntitlementsOut(BaseModel):
    keys: list[str]
