from pydantic import BaseModel


class InventoryRead(BaseModel):
    id: int
    name: str
    stock_qty: int


class InventoryCreateResponse(BaseModel):
    id: int
    name: str
