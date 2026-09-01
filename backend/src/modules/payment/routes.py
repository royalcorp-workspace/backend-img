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

class PaymentStatusResponse(BaseModel):
    order_id: uuid.UUID = Field(..., example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    payment_status: int | None = Field(..., example=2)
    status: int = Field(..., example=2)
    is_paid: bool = Field(..., example=True)

class EspayCheckoutRequest(BaseModel):
    order_id: uuid.UUID = Field(..., example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    payment_method_code: str = Field(..., example="BCAATM")

class EspayCheckoutResponse(BaseModel):
    success: bool
    payment: dict[str, Any]
    redirect_url: str
    va_number: str | None = None
    va_expired: str | None = None
    
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
                "redirect_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM",
                "va_number": "1234567890123456",
                "va_expired": "2026-09-02 10:00:00"
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
                        "redirect_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM",
                        "va_number": "1234567890123456",
                        "va_expired": "2026-09-02 10:00:00"
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
    from ...infrastructure.config.settings import settings
    import httpx
    import datetime
    
    stmt = select(Order).where(Order.id == request.order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    amount = f"{float(order.total):.2f}"
    
    base_url = settings.ESPAY_BASE_URL.rstrip('/')
    espay_url = base_url.replace('/rest/merchant', '/rest/merchantpg') + '/sendinvoice'
    
    signature_key = settings.ESPAY_SIGNATURE_KEY
    comm_code = settings.ESPAY_MERCHANT_KEY
    rq_uuid = str(uuid.uuid4())
    rq_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    espay_order_id = order.order_number.replace("-", "") if order.order_number else str(order.id).replace("-", "")
    
    data_to_hash = f"##{signature_key}##{rq_uuid}##{rq_datetime}##{espay_order_id}##{amount}##IDR##{comm_code}##SENDINVOICE##"
    signature = hashlib.sha256(data_to_hash.upper().encode()).hexdigest()
    
    payload = {
        'rq_uuid': rq_uuid,
        'rq_datetime': rq_datetime,
        'order_id': espay_order_id,
        'amount': amount,
        'ccy': 'IDR',
        'comm_code': comm_code,
        'remark1': '00000000000',
        'remark2': 'Customer',
        'remark3': '',
        'update': 'N',
        'bank_code': request.payment_method_code,
        'va_expired': 1440,
        'signature': signature,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(espay_url, data=payload)
            payment_data = response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to communicate with Espay: {str(e)}")
            
    if response.status_code == 200 and payment_data.get('error_code') == '0000':
        va_number = payment_data.get('va_number')
        
        # Determine expiration timestamp based on rq_datetime + 1440 mins
        expired_date_dt = datetime.datetime.strptime(rq_datetime, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(minutes=1440)
        va_expired = expired_date_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Update order in DB
        order.payment_status = 1
        meta = order.meta or {}
        meta['espay_reference'] = payment_data.get('reference', '')
        meta['va_number'] = va_number
        order.meta = meta
        await db.commit()
        
        return {
            "success": True,
            "payment": payment_data,
            "redirect_url": payment_data.get("payment_url", ""),
            "va_number": va_number,
            "va_expired": va_expired
        }
    else:
        raise HTTPException(status_code=400, detail=f"Espay Error: {payment_data.get('error_desc', 'Unknown')}")

@router.get(
    "/espay/status/{order_id}",
    response_model=PaymentStatusResponse,
    summary="Check Payment Status",
    description="Check the payment status of an order directly from the database.",
    responses={
        200: {
            "description": "Payment status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "order_id": "8f30c3a2-b911-4a4b-841a-e4b51a5c6d70",
                        "payment_status": 2,
                        "status": 2,
                        "is_paid": True
                    }
                }
            }
        },
        404: {
            "description": "Order not found"
        }
    }
)
async def check_payment_status(
    order_id: uuid.UUID,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Assuming payment_status 2 or status 2 means PAID based on typical convention
    # Adjust the logic if your DB uses different constants for PAID.
    is_paid = (order.payment_status == 2) or (order.status == 2)
    
    return {
        "order_id": order.id,
        "payment_status": order.payment_status,
        "status": order.status,
        "is_paid": is_paid
    }

