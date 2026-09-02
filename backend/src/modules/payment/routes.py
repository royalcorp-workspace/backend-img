from typing import Any, Annotated
import uuid
import hashlib
import time
import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, String
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.config.settings import settings
from ...infrastructure.dependencies import AsyncSessionDep
from ..order.models import Order
from ..payment_method.models import PaymentMethod
from ..payment_method.service import (
    PAYMENT_METHOD_TYPES,
    resolve_payment_type_name,
    resolve_cara_bayar,
)
from ..add_to_cart.models import AddToCart

router = APIRouter(prefix="/payment", tags=["Payment"])


# Schemas
class PaymentStatusResponse(BaseModel):
    order_id: uuid.UUID = Field(..., example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    payment_status: int | None = Field(..., example=2)
    status: int = Field(..., example=2)
    is_paid: bool = Field(..., example=True)


class EspayCheckoutRequest(BaseModel):
    order_id: uuid.UUID = Field(..., example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    payment_method_code: str = Field(..., example="BCAATM")
    add_to_cart_id: uuid.UUID | None = Field(None, example="323e4567-e89b-12d3-a456-426614174002", description="Optional AddToCart ID to delete upon checkout")


class PaymentMethodDetail(BaseModel):
    id: uuid.UUID | str | None = Field(None, example="019f5933-08c8-7082-b1cd-7185cff32192")
    code: str = Field(..., example="BCAATM")
    name: str = Field(..., example="BCA Virtual Account")
    type: int | None = Field(None, example=2)
    type_name: str | None = Field(None, example="Virtual Account")
    bank_name: str | None = Field(None, example="BCA")
    provider: str | None = Field(None, example="Espay")
    image: str | None = Field(None, example="https://example.com/bca.png")
    has_charge: bool = Field(False, example=False)
    charge_type: int | None = Field(None, example=1)
    charge_value: float | None = Field(0.0, example=0.0)
    charge_bearer: str | None = Field(None, example="customer")
    minimum_amount: float | None = Field(0.0, example=10000.0)
    maximum_amount: float | None = Field(None, example=None)
    bank_info: dict[str, Any] | list[Any] | Any | None = Field(None)
    instructions: dict[str, Any] | list[Any] | Any | None = Field(None)
    cara_bayar: list[str] | None = Field(None)


class EspayPaymentData(BaseModel):
    id: str | None = Field(None, example="1a2b3c4d-5e6f-7g8h-9i0j-k1l2m3n4o5p6")
    order_id: str = Field(..., example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    order_number: str | None = Field(None, example="ORD-20260828-001")
    payment_method: str = Field(..., example="BCAATM")
    bank_name: str | None = Field(None, example="BCA")
    type: int | None = Field(None, example=2)
    type_name: str | None = Field(None, example="Virtual Account")
    amount: float = Field(..., example=2500000.00)
    status: str = Field(..., example="pending")
    reference: str = Field(..., example="PAY-1724808000")
    payment_url: str = Field(..., example="https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM")
    cara_bayar: list[str] | None = Field(None)
    payment_method_detail: PaymentMethodDetail | None = Field(None)


class EspayCheckoutResponse(BaseModel):
    success: bool = Field(..., example=True)
    payment: dict[str, Any] | EspayPaymentData
    redirect_url: str = Field(..., example="https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM")
    va_number: str | None = Field(None, example="1234567890123456")
    va_expired: str | None = Field(None, example="2026-09-02 10:00:00")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "payment": {
                    "id": "1a2b3c4d-5e6f-7g8h-9i0j-k1l2m3n4o5p6",
                    "order_id": "8f30c3a2-b911-4a4b-841a-e4b51a5c6d70",
                    "order_number": "ORD-20260828-001",
                    "payment_method": "BCAATM",
                    "bank_name": "BCA",
                    "type": 2,
                    "type_name": "Virtual Account",
                    "amount": 2500000.00,
                    "status": "pending",
                    "reference": "PAY-1724808000",
                    "payment_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM",
                    "cara_bayar": [
                        "Buka aplikasi Mobile Banking BCA atau kunjungi ATM BCA terdekat.",
                        "Pilih menu Transfer / Pembayaran > Virtual Account (BCA Virtual Account).",
                        "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
                        "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
                        "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
                        "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
                    ],
                    "payment_method_detail": {
                        "id": "019f5933-08c8-7082-b1cd-7185cff32192",
                        "code": "BCAATM",
                        "name": "BCA Virtual Account",
                        "type": 2,
                        "type_name": "Virtual Account",
                        "bank_name": "BCA",
                        "provider": "Espay",
                        "image": "https://example.com/bca.png",
                        "has_charge": False,
                        "charge_type": 1,
                        "charge_value": 0.0,
                        "charge_bearer": "customer",
                        "minimum_amount": 10000.0,
                        "maximum_amount": None,
                        "bank_info": {
                            "bank_name": "BCA",
                            "bank_code": "014",
                            "account_name": "PT ROYAL CORP",
                        },
                        "instructions": [
                            "Buka aplikasi Mobile Banking BCA atau kunjungi ATM BCA terdekat.",
                            "Pilih menu Transfer / Pembayaran > Virtual Account (BCA Virtual Account).",
                            "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
                            "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
                            "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
                            "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
                        ],
                        "cara_bayar": [
                            "Buka aplikasi Mobile Banking BCA atau kunjungi ATM BCA terdekat.",
                            "Pilih menu Transfer / Pembayaran > Virtual Account (BCA Virtual Account).",
                            "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
                            "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
                            "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
                            "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
                        ],
                    },
                },
                "redirect_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM",
                "va_number": "1234567890123456",
                "va_expired": "2026-09-02 10:00:00",
            }
        }


ESPAY_CHECKOUT_EXAMPLE = {
    "success": True,
    "payment": {
        "id": "1a2b3c4d-5e6f-7g8h-9i0j-k1l2m3n4o5p6",
        "order_id": "8f30c3a2-b911-4a4b-841a-e4b51a5c6d70",
        "order_number": "ORD-20260828-001",
        "payment_method": "BCAATM",
        "bank_name": "BCA",
        "type": 2,
        "type_name": "Virtual Account",
        "amount": 2500000.00,
        "status": "pending",
        "reference": "PAY-1724808000",
        "payment_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM",
        "cara_bayar": [
            "Buka aplikasi Mobile Banking BCA atau kunjungi ATM BCA terdekat.",
            "Pilih menu Transfer / Pembayaran > Virtual Account (BCA Virtual Account).",
            "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
            "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
            "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
            "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
        ],
        "payment_method_detail": {
            "id": "019f5933-08c8-7082-b1cd-7185cff32192",
            "code": "BCAATM",
            "name": "BCA Virtual Account",
            "type": 2,
            "type_name": "Virtual Account",
            "bank_name": "BCA",
            "provider": "Espay",
            "image": "https://example.com/bca.png",
            "has_charge": False,
            "charge_type": 1,
            "charge_value": 0.0,
            "charge_bearer": "customer",
            "minimum_amount": 10000.0,
            "maximum_amount": None,
            "bank_info": {
                "bank_name": "BCA",
                "bank_code": "014",
                "account_name": "PT ROYAL CORP",
            },
            "instructions": [
                "Buka aplikasi Mobile Banking BCA atau kunjungi ATM BCA terdekat.",
                "Pilih menu Transfer / Pembayaran > Virtual Account (BCA Virtual Account).",
                "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
                "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
                "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
                "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
            ],
            "cara_bayar": [
                "Buka aplikasi Mobile Banking BCA atau kunjungi ATM BCA terdekat.",
                "Pilih menu Transfer / Pembayaran > Virtual Account (BCA Virtual Account).",
                "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
                "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
                "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
                "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
            ],
        },
    },
    "redirect_url": "https://sandbox-api.espay.id/checkout/ORD-20260828-001?bank=BCAATM",
    "va_number": "1234567890123456",
    "va_expired": "2026-09-02 10:00:00",
}


@router.post(
    "/espay/checkout",
    response_model=EspayCheckoutResponse,
    summary="Espay Checkout",
    description="Initialize payment checkout via Espay with payment method details, instructions, bank name, type, and optional cart cleanup.",
    responses={
        200: {
            "description": "Successful checkout initialization",
            "content": {
                "application/json": {
                    "example": ESPAY_CHECKOUT_EXAMPLE
                }
            },
        },
        404: {
            "description": "Order or Payment Method not found",
        },
    },
)
async def espay_checkout(
    request: EspayCheckoutRequest,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    # 1. Fetch Order
    stmt = select(Order).where(Order.id == request.order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2. Fetch Payment Method by code
    pm_stmt = select(PaymentMethod).where(
        PaymentMethod.code == request.payment_method_code,
        PaymentMethod.deleted == False,
    )
    pm_result = await db.execute(pm_stmt)
    payment_method = pm_result.scalar_one_or_none()

    if not payment_method:
        pm_stmt_any = select(PaymentMethod).where(PaymentMethod.code == request.payment_method_code)
        pm_res_any = await db.execute(pm_stmt_any)
        payment_method = pm_res_any.scalar_one_or_none()

    if not payment_method:
        raise HTTPException(
            status_code=404,
            detail=f"Payment method '{request.payment_method_code}' not found",
        )

    # 3. Resolve details (bank_name, bank_code, type_name, cara_bayar)
    bank_info = payment_method.bank_info if isinstance(payment_method.bank_info, dict) else {}
    bank_name = (
        bank_info.get("bank_name")
        or bank_info.get("bank")
        or payment_method.name
    )
    bank_code = bank_info.get("bank_code", request.payment_method_code)
    type_name = resolve_payment_type_name(payment_method.type)
    cara_bayar = resolve_cara_bayar(
        payment_method,
        pm_type=payment_method.type,
        pm_name=payment_method.name,
        bank_name=bank_name,
        instructions=payment_method.instructions,
    )

    # 4. Prepare Espay API call
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
        'bank_code': bank_code,
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
        order.payment_method = payment_method.code
        order.payment_status = 1
        meta = order.meta or {}
        meta['espay_reference'] = payment_data.get('reference', '')
        meta['va_number'] = va_number
        order.meta = meta

        # Remove AddToCart if specific add_to_cart_id is provided in request or order.meta
        target_cart_ids: list[uuid.UUID] = []
        if request.add_to_cart_id:
            target_cart_ids.append(request.add_to_cart_id)

        if isinstance(order.meta, dict):
            cart_id_meta = order.meta.get("add_to_cart_id") or order.meta.get("cart_id")
            if cart_id_meta:
                try:
                    cart_uuid = uuid.UUID(str(cart_id_meta))
                    if cart_uuid not in target_cart_ids:
                        target_cart_ids.append(cart_uuid)
                except (ValueError, TypeError):
                    pass

        for cart_id in target_cart_ids:
            stmt_cart = select(AddToCart).where(AddToCart.id == cart_id)
            res_cart = await db.execute(stmt_cart)
            cart = res_cart.scalar_one_or_none()
            if cart:
                await db.delete(cart)

        await db.commit()

        payment_method_detail = {
            "id": payment_method.id,
            "code": payment_method.code,
            "name": payment_method.name,
            "type": payment_method.type,
            "type_name": type_name,
            "bank_name": bank_name,
            "provider": payment_method.provider,
            "image": payment_method.image,
            "has_charge": payment_method.has_charge,
            "charge_type": payment_method.charge_type,
            "charge_value": payment_method.charge_value,
            "charge_bearer": payment_method.charge_bearer,
            "minimum_amount": payment_method.minimum_amount,
            "maximum_amount": payment_method.maximum_amount,
            "bank_info": payment_method.bank_info,
            "instructions": payment_method.instructions,
            "cara_bayar": cara_bayar,
        }

        # Enrich payment response with additional requested fields
        payment_result = dict(payment_data)
        payment_result.update({
            "order_id": str(order.id),
            "order_number": order.order_number,
            "payment_method": payment_method.code,
            "bank_name": bank_name,
            "type": payment_method.type,
            "type_name": type_name,
            "amount": float(order.total),
            "status": "pending",
            "reference": payment_data.get("reference", f"PAY-{int(time.time())}"),
            "payment_url": payment_data.get("payment_url", ""),
            "cara_bayar": cara_bayar,
            "payment_method_detail": payment_method_detail,
        })

        return {
            "success": True,
            "payment": payment_result,
            "redirect_url": payment_data.get("payment_url", ""),
            "va_number": va_number,
            "va_expired": va_expired,
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
                        "is_paid": True,
                    }
                }
            },
        },
        404: {
            "description": "Order not found",
        },
    },
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
        "is_paid": is_paid,
    }





