from pydantic import BaseModel

class Algorithm(BaseModel):
    name: str 
    crop_type: str