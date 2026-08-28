from typing import Any, Annotated
import uuid
import hashlib
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..order.models import Order
from sqlalchemy import select

router = APIRouter(prefix="/payment", tags=["Payment"])

from ...infrastructure.dependencies import AsyncSessionDep

ESPAY_SIGNATURE_KEY = "dummy_signature_key" # Replace with actual from settings

from pydantic import BaseModel, Field

class EspayCheckoutRequest(BaseModel):
    order_id: uuid.UUID = Field(..., example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    payment_method_code: str = Field(..., example="BCAATM")

class EspayCheckoutResponse(BaseModel):
    success: bool
    payment: dict[str, Any]
    redirect_url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "payment": {
                    "id": "1a2b3c4d-5e6f-7g8h-9i0j-k1l2m3n4o5p6",
                    "order_id": "ORD-20260828-001",
                    "payment_method": "BCAATM",
                    "amount": 2500000.00,
                    "status": "pending",
                    "reference": "PAY-1724808000",
                    "payment_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM"
                },
                "redirect_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM"
            }
        }

@router.post(
    "/espay/checkout", 
    response_model=EspayCheckoutResponse,
    responses={
        200: {
            "description": "Successful checkout initialization",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "payment": {
                            "id": "1a2b3c4d-5e6f-7g8h-9i0j-k1l2m3n4o5p6",
                            "order_id": "ORD-20260828-001",
                            "payment_method": "BCAATM",
                            "amount": 2500000.00,
                            "status": "pending",
                            "reference": "PAY-1724808000",
                            "payment_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM"
                        },
                        "redirect_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM"
                    }
                }
            }
        }
    }
)
async def espay_checkout(
    request: EspayCheckoutRequest,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    stmt = select(Order).where(Order.id == request.order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    amount = float(order.total)
    reference = f"PAY-{int(time.time())}"
    
    payment_data = {
        "id": str(uuid.uuid4()),
        "order_id": order.order_number,
        "payment_method": request.payment_method_code,
        "amount": amount,
        "status": "pending",
        "reference": reference,
        "payment_url": f"https://sandbox-api.espay.id/checkout/{order.order_number}?bank={request.payment_method_code}"
    }
    
    return {
        "success": True,
        "payment": payment_data,
        "redirect_url": payment_data["payment_url"]
    }