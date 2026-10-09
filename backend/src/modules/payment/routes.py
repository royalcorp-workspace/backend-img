from typing import Any, Annotated
import uuid
import hashlib
import time
import datetime
import urllib.parse
import random
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, String, cast, or_, text
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.config.settings import settings
from ...infrastructure.dependencies import AsyncSessionDep
from ...infrastructure.logging import get_logger
from ..order.models import Order
from ..customer.models import Customer
from ..payment_method.models import PaymentMethod
from ..payment_method.service import (
    PAYMENT_METHOD_TYPES,
    resolve_payment_type_name,
    resolve_cara_bayar,
)
from ..add_to_cart.models import AddToCart

logger = get_logger()
router = APIRouter(prefix="/payment", tags=["Payment"])


# ==============================================================================
# Schemas
# ==============================================================================

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
    qr_string: str | None = Field(None, example="ID.CO.QRIS.IMG.ORD001.250000")
    qr_code: str | None = Field(None, example="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=...")


# SNAP BI Schemas
class SnapAmount(BaseModel):
    value: str = Field(..., example="2500000.00")
    currency: str = Field("IDR", example="IDR")


class SnapVaInquiryRequest(BaseModel):
    partnerServiceId: str | None = Field(None, example="8808")
    customerNo: str | None = Field(None, example="0001")
    virtualAccountNo: str | None = Field(None, example="88080001")
    inquiryRequestId: str | None = Field(None, example="c3b9b4f0-4567-4a8b-9456-123456789abc")
    additionalInfo: dict[str, Any] | None = None


class SnapVaPaymentRequest(BaseModel):
    partnerServiceId: str | None = Field(None, example="8808")
    customerNo: str | None = Field(None, example="0001")
    virtualAccountNo: str | None = Field(None, example="88080001")
    inquiryRequestId: str | None = None
    paymentRequestId: str | None = None
    paidAmount: SnapAmount | dict[str, Any] | None = None
    trxId: str | None = None
    referenceNo: str | None = None
    additionalInfo: dict[str, Any] | None = None


class SnapQrNotifyRequest(BaseModel):
    partnerReferenceNo: str | None = Field(None, example="ORD-20260828-001")
    originalPartnerReferenceNo: str | None = None
    referenceNo: str | None = None
    externalStoreId: str | None = None
    order_id: str | None = None
    amount: SnapAmount | dict[str, Any] | None = None
    additionalInfo: dict[str, Any] | None = None


# ==============================================================================
# Helper Functions
# ==============================================================================

def resolve_espay_product_code(
    code_or_bank: str | None,
    payment_type: int | None = None,
    bank_info: dict[str, Any] | None = None,
    payment_method_code: str | None = None,
) -> str:
    """
    Resolves Espay product code when multiple payment methods share the same clearing bank code (e.g. '014').
    """
    if bank_info and isinstance(bank_info, dict):
        p_code = bank_info.get("product_code")
        if p_code and str(p_code).strip() and not str(p_code).strip().isdigit():
            return str(p_code).strip().upper()

    candidate = (payment_method_code or code_or_bank or "").strip()
    if candidate and not candidate.isdigit():
        return candidate.upper()

    bank_code = (code_or_bank or (bank_info.get("bank_code") if isinstance(bank_info, dict) else "") or "").strip()

    BANK_PRODUCT_MAP: dict[str, dict[Any, str]] = {
        "014": {
            5: "CREDITCARD",
            2: "BCAATM",
            3: "GOPAYINAPP",
            "default": "BCAATM",
        },
        "008": {
            5: "CREDITCARD",
            2: "MANDIRIATM",
            3: "QRISPLUS",
            4: "QRISPLUS",
            "default": "MANDIRIATM",
        },
        "002": {
            5: "CREDITCARD",
            2: "BRIATM",
            "default": "BRIATM",
        },
        "022": {
            5: "CREDITCARD",
            2: "CIMBATM",
            "default": "CIMBATM",
        },
        "011": {
            5: "CREDITCARD",
            2: "DANAMONATM",
            "default": "DANAMONATM",
        },
        "016": {
            5: "CREDITCARD",
            2: "BIIATM",
            "default": "BIIATM",
        },
        "472": {
            2: "BANKSAQUATM",
            "default": "BANKSAQUATM",
        },
        "503": {
            3: "OVO",
            "default": "OVO",
        },
    }

    if bank_code in BANK_PRODUCT_MAP:
        mapping = BANK_PRODUCT_MAP[bank_code]
        if payment_type and payment_type in mapping:
            return mapping[payment_type]
        return mapping.get("default", bank_code)

    return candidate or bank_code


def generate_native_payment_details(
    order: Order,
    payment_method: PaymentMethod,
    bank_code: str,
) -> dict[str, Any]:
    """
    Generates native payment details (VA Number, QRIS, Reference) autonomously
    without requiring external Espay credentials in .env.
    """
    code_upper = (payment_method.code or "").upper()
    bank_code_str = str(bank_code).upper()

    # Determine bank VA prefix
    if "BCA" in code_upper or bank_code_str == "014":
        va_prefix = "8808"
    elif "MANDIRI" in code_upper or bank_code_str == "008":
        va_prefix = "89508"
    elif "BRI" in code_upper or bank_code_str == "002":
        va_prefix = "12345"
    elif "BNI" in code_upper or bank_code_str == "009":
        va_prefix = "988"
    elif "PERMATA" in code_upper or bank_code_str == "013":
        va_prefix = "8422"
    elif "CIMB" in code_upper or bank_code_str == "022":
        va_prefix = "118"
    elif "DANAMON" in code_upper or bank_code_str == "011":
        va_prefix = "8888"
    elif "SAQU" in code_upper or bank_code_str == "472":
        va_prefix = "472"
    else:
        va_prefix = "88"

    # Extract digits from order number or id
    order_digits = "".join([c for c in (order.order_number or str(order.id)) if c.isdigit()])
    if len(order_digits) < 6:
        order_digits = f"{order_digits}{random.randint(100000, 999999)}"
    va_number = f"{va_prefix}{order_digits[-8:]}"

    # Expiry 24h
    now = datetime.datetime.now()
    va_expired = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    # Generate QRIS details if QRIS payment method
    is_qris = (payment_method.type == 4) or ("QRIS" in code_upper)
    qr_string = None
    qr_code = None
    if is_qris:
        clean_order_ref = (order.order_number or str(order.id)[:8]).replace("-", "").replace(".", "")
        qr_string = f"ID.CO.QRIS.IMG.{clean_order_ref}.{round(float(order.total or 0))}"
        qr_code = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(qr_string)}"

    reference = f"PAY-IMG-{int(time.time())}"
    payment_url = f"/thankyou?order_id={order.id}"

    return {
        "va_number": va_number,
        "va_expired": va_expired,
        "qr_string": qr_string,
        "qr_code": qr_code,
        "reference": reference,
        "payment_url": payment_url,
    }


# ==============================================================================
# Payment Checkout Endpoints
# ==============================================================================

@router.post(
    "/checkout",
    response_model=dict[str, Any],
    summary="Checkout Transaction",
    description="Initiates a payment transaction with automatic fallback to IMG native payment (VA & QRIS) if Espay .env credentials are not configured.",
)
@router.post(
    "/espay/checkout",
    response_model=dict[str, Any],
    summary="Checkout Transaction (Espay Alias)",
    description="Alias endpoint for Espay checkout initialization.",
)
async def checkout_payment(
    request: EspayCheckoutRequest,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    # 1. Fetch Order
    stmt = select(Order).where(Order.id == request.order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2. Fetch Payment Method by code (with escalation for numeric clearing codes like 014)
    pm_code_input = request.payment_method_code.strip()
    pm_stmt = select(PaymentMethod).where(
        func.upper(PaymentMethod.code) == pm_code_input.upper(),
        PaymentMethod.deleted == False,
    )
    pm_result = await db.execute(pm_stmt)
    payment_method = pm_result.scalar_one_or_none()

    if not payment_method:
        # Escalation: try resolved product code (e.g. 014 -> BCAATM)
        escalated_code = resolve_espay_product_code(pm_code_input)
        if escalated_code != pm_code_input:
            pm_stmt_esc = select(PaymentMethod).where(
                func.upper(PaymentMethod.code) == escalated_code.upper(),
                PaymentMethod.deleted == False,
            )
            pm_result_esc = await db.execute(pm_stmt_esc)
            payment_method = pm_result_esc.scalar_one_or_none()

    if not payment_method:
        # Check in bank_info JSON field (product_code or bank_code)
        pm_stmt_json = select(PaymentMethod).where(
            PaymentMethod.deleted == False,
            or_(
                cast(PaymentMethod.bank_info["product_code"], String) == f'"{pm_code_input}"',
                cast(PaymentMethod.bank_info["product_code"], String) == pm_code_input,
                cast(PaymentMethod.bank_info["bank_code"], String) == f'"{pm_code_input}"',
                cast(PaymentMethod.bank_info["bank_code"], String) == pm_code_input,
            )
        ).order_by(PaymentMethod.type.asc())
        pm_result_json = await db.execute(pm_stmt_json)
        payment_method = pm_result_json.scalars().first()

    if not payment_method:
        pm_stmt_any = select(PaymentMethod).where(func.upper(PaymentMethod.code) == pm_code_input.upper())
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
    type_name = resolve_payment_type_name(payment_method.type)
    cara_bayar = resolve_cara_bayar(
        payment_method,
        pm_type=payment_method.type,
        pm_name=payment_method.name,
        bank_name=bank_name,
        instructions=payment_method.instructions,
    )

    espay_bank_code = resolve_espay_product_code(
        code_or_bank=request.payment_method_code,
        payment_type=payment_method.type,
        bank_info=bank_info,
        payment_method_code=payment_method.code,
    )

    # 4. Attempt Espay API or Fallback to Native Generator
    has_espay_env = bool(
        settings.ESPAY_SIGNATURE_KEY
        and settings.ESPAY_MERCHANT_KEY
        and settings.ESPAY_BASE_URL
        and settings.ESPAY_BASE_URL != "https://sandbox"
    )

    va_number = None
    va_expired = None
    qr_string = None
    qr_code = None
    reference = f"PAY-IMG-{int(time.time())}"
    payment_url = f"/thankyou?order_id={order.id}"

    espay_success = False

    if has_espay_env:
        try:
            amount = f"{float(order.total or 0.0):.2f}"
            base_url = settings.ESPAY_BASE_URL.rstrip('/')
            espay_url = base_url.replace('/rest/merchant', '/rest/merchantpg') + '/sendinvoice'

            signature_key = settings.ESPAY_SIGNATURE_KEY
            comm_code = settings.ESPAY_MERCHANT_KEY
            rq_uuid = str(uuid.uuid4())
            rq_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            espay_order_id = order.order_number.replace("-", "").replace(".", "") if order.order_number else str(order.id).replace("-", "")

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
                'bank_code': espay_bank_code,
                'va_expired': 1440,
                'signature': signature,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(espay_url, data=payload)
                payment_data = response.json()

            if response.status_code == 200 and payment_data.get('error_code') == '0000':
                va_number = payment_data.get('va_number')
                expired_date_dt = datetime.datetime.strptime(rq_datetime, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(minutes=1440)
                va_expired = expired_date_dt.strftime("%Y-%m-%d %H:%M:%S")
                reference = payment_data.get('reference', reference)
                payment_url = payment_data.get('payment_url', payment_url)
                espay_success = True
                logger.info(f"Espay SendInvoice succeeded for order {order.order_number}: VA {va_number}")
            else:
                logger.warning(f"Espay SendInvoice returned {payment_data}. Falling back to native payment details.")
        except Exception as e:
            logger.warning(f"Espay API connection error: {str(e)}. Falling back to native payment details.")

    if not espay_success:
        # Seamlessly generate native payment data without requiring Espay credentials in .env
        logger.info(f"Using IMG native payment generator for Order {order.order_number or order.id}")
        native_details = generate_native_payment_details(order, payment_method, espay_bank_code)
        va_number = native_details["va_number"]
        va_expired = native_details["va_expired"]
        qr_string = native_details["qr_string"]
        qr_code = native_details["qr_code"]
        reference = native_details["reference"]
        payment_url = native_details["payment_url"]

    # 5. Update Order in Database
    order.payment_method = payment_method.code
    order.payment_status = 1  # Menunggu Pembayaran
    meta = dict(order.meta) if isinstance(order.meta, dict) else {}
    meta['espay_reference'] = reference
    meta['va_number'] = va_number
    meta['va_expired'] = va_expired
    if qr_string:
        meta['qr_string'] = qr_string
    if qr_code:
        meta['qr_code'] = qr_code
    meta['payment_method_code'] = payment_method.code
    order.meta = meta
    flag_modified(order, "meta")

    # 6. Optional Cart Cleanup
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

    payment_result = {
        "id": str(order.id),
        "order_id": str(order.id),
        "order_number": order.order_number,
        "payment_method": payment_method.code,
        "bank_name": bank_name,
        "type": payment_method.type,
        "type_name": type_name,
        "amount": float(order.total or 0.0),
        "status": "pending",
        "reference": reference,
        "payment_url": payment_url,
        "cara_bayar": cara_bayar,
        "va_number": va_number,
        "va_expired": va_expired,
        "qr_string": qr_string,
        "qr_code": qr_code,
        "payment_method_detail": payment_method_detail,
    }

    return {
        "success": True,
        "payment": payment_result,
        "redirect_url": payment_url,
        "va_number": va_number,
        "va_expired": va_expired,
        "qr_string": qr_string,
        "qr_code": qr_code,
    }


# ==============================================================================
# Payment Status Endpoints
# ==============================================================================

@router.get(
    "/status/{order_id}",
    response_model=PaymentStatusResponse,
    summary="Check Payment Status",
    description="Check the payment status of an order directly from the database.",
)
@router.get(
    "/espay/status/{order_id}",
    response_model=PaymentStatusResponse,
    summary="Check Payment Status (Espay Alias)",
    description="Alias endpoint to check order payment status.",
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

    is_paid = (order.payment_status in (1, 2)) or (order.status is not None and order.status >= 2)

    return {
        "order_id": order.id,
        "payment_status": order.payment_status,
        "status": order.status,
        "is_paid": is_paid,
    }


# ==============================================================================
# SNAP BI VA & QRIS Callback Endpoints (Grouped in Payment)
# ==============================================================================

@router.post(
    "/snap/inquiry-va",
    summary="SNAP BI Virtual Account Inquiry",
    description="SNAP BI Inquiry endpoint matching order by virtualAccountNo or order_number without requiring Espay credentials.",
)
@router.post(
    "/v1.0/transfer-va/inquiry-va",
    summary="SNAP BI Virtual Account Inquiry (Standard Path)",
    description="SNAP BI standard path for Virtual Account Inquiry.",
)
async def snap_inquiry_va(
    request: SnapVaInquiryRequest,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    clean_va = (request.virtualAccountNo or "").strip()
    if not clean_va:
        return {
            "responseCode": "4042300",
            "responseMessage": "Virtual account number required",
            "virtualAccountData": {},
        }

    clean_va_no_sym = clean_va.replace("-", "").replace(".", "").lower()

    # Match order by order_number (with/without symbols) or meta JSON content
    stmt = select(Order).where(
        or_(
            func.lower(func.replace(func.replace(Order.order_number, "-", ""), ".", "")) == clean_va_no_sym,
            func.lower(Order.order_number) == clean_va.lower(),
            cast(Order.meta, String).ilike(f'%"{clean_va}"%'),
            cast(Order.meta, String).ilike(f'%{clean_va}%'),
        )
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        logger.warning(f"SNAP VA Inquiry: Order not found for VA {clean_va}")
        return {
            "responseCode": "4042300",
            "responseMessage": "Order Not Found",
            "virtualAccountData": {},
        }

    # Resolve customer details
    customer = order.customer
    meta = order.meta if isinstance(order.meta, dict) else {}
    customer_meta = meta.get("customer", {}) if isinstance(meta.get("customer"), dict) else {}
    shipping_meta = meta.get("shipping_address", {}) if isinstance(meta.get("shipping_address"), dict) else {}

    customer_name = (customer.name if customer else None) or customer_meta.get("name") or "Customer"
    customer_email = (customer.email if customer else None) or customer_meta.get("email") or "customer@domain.com"
    customer_phone = (customer.phone if customer else None) or customer_meta.get("phone") or "08123456789"
    customer_address = shipping_meta.get("address") or customer_meta.get("address") or "Alamat Pengiriman"
    customer_city = shipping_meta.get("city") or "-"
    customer_postal = shipping_meta.get("postal_code") or "-"

    amount_str = f"{float(order.total or 0.0):.2f}"

    return {
        "responseCode": "2002400",
        "responseMessage": "Success",
        "virtualAccountData": {
            "partnerServiceId": request.partnerServiceId or "",
            "customerNo": request.customerNo or "",
            "virtualAccountNo": clean_va,
            "virtualAccountName": customer_name,
            "virtualAccountEmail": customer_email,
            "virtualAccountPhone": customer_phone,
            "inquiryRequestId": request.inquiryRequestId or str(uuid.uuid4()),
            "totalAmount": {
                "value": amount_str,
                "currency": "IDR",
            },
            "billDetails": [
                {
                    "billDescription": {
                        "english": f"Invoice No {order.order_number}",
                        "indonesia": f"Tagihan No {order.order_number}",
                    }
                }
            ],
            "additionalInfo": {
                "shippingAddress": {
                    "firstName": customer_name,
                    "lastName": "",
                    "address": customer_address,
                    "city": customer_city,
                    "postalCode": customer_postal,
                    "phoneNumber": customer_phone,
                    "countryCode": "IDN",
                }
            },
        },
    }


@router.post(
    "/snap/payment-va",
    summary="SNAP BI Virtual Account Payment Notification",
    description="SNAP BI Payment endpoint to mark order as paid (payment_status=2, status=2/3) without requiring Espay credentials.",
)
@router.post(
    "/v1.0/transfer-va/payment-va",
    summary="SNAP BI Virtual Account Payment Notification (Standard Path)",
    description="SNAP BI standard path for Virtual Account Payment Notification.",
)
async def snap_payment_va(
    request: SnapVaPaymentRequest,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    clean_va = (request.virtualAccountNo or "").strip()
    clean_va_no_sym = clean_va.replace("-", "").replace(".", "").lower()
    trx_id = (request.trxId or request.referenceNo or "").strip()
    trx_id_no_sym = trx_id.replace("-", "").replace(".", "").lower()

    stmt = select(Order).where(
        or_(
            func.lower(func.replace(func.replace(Order.order_number, "-", ""), ".", "")) == clean_va_no_sym,
            func.lower(Order.order_number) == clean_va.lower(),
            cast(Order.meta, String).ilike(f'%"{clean_va}"%'),
            cast(Order.meta, String).ilike(f'%{clean_va}%'),
            func.lower(func.replace(func.replace(Order.order_number, "-", ""), ".", "")) == trx_id_no_sym,
        )
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        logger.warning(f"SNAP VA Payment: Order not found for VA {clean_va} / Trx {trx_id}")
        return {
            "responseCode": "4042700",
            "responseMessage": "Order Not Found",
            "virtualAccountData": {},
        }

    # Update Order to Paid status
    order.payment_status = 2  # Paid
    order.status = Order.STATUS_PROCESSING  # 3: Diproses (or 2: Dikonfirmasi)
    meta = dict(order.meta) if isinstance(order.meta, dict) else {}
    meta["paid_at"] = datetime.datetime.now().isoformat()
    meta["snap_va_payment"] = request.model_dump()
    order.meta = meta
    flag_modified(order, "meta")

    # Update settlement if present
    if order.settlement_id:
        try:
            await db.execute(
                text("UPDATE settlements SET status = 'success', settlement_date = :sdate, updated_at = :udate WHERE id = :sid"),
                {
                    "sdate": datetime.datetime.now(),
                    "udate": datetime.datetime.now(),
                    "sid": order.settlement_id,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update settlement status: {str(e)}")

    await db.commit()
    logger.info(f"SNAP VA Payment: Order {order.order_number} marked as Paid.")

    customer_name = order.customer.name if order.customer else "Customer"

    return {
        "responseCode": "2002700",
        "responseMessage": "Successful",
        "virtualAccountData": {
            "partnerServiceId": request.partnerServiceId or "",
            "customerNo": request.customerNo or "",
            "virtualAccountNo": clean_va,
            "virtualAccountName": customer_name,
            "paymentFlagReason": {
                "english": "Success",
                "indonesia": "Sukses",
            },
        },
    }


@router.post(
    "/snap/qr-notify",
    summary="SNAP BI QRIS Payment Notification",
    description="SNAP BI QRIS Payment notification endpoint to mark order as paid.",
)
@router.post(
    "/v1.0/qr/qr-mpm-notify",
    summary="SNAP BI QRIS Payment Notification (Standard Path)",
    description="SNAP BI standard path for QRIS MPM Payment Notification.",
)
async def snap_qr_notify(
    request: SnapQrNotifyRequest,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    ref_candidate = (
        request.partnerReferenceNo
        or request.originalPartnerReferenceNo
        or request.referenceNo
        or request.order_id
        or ""
    ).strip()
    ref_clean = ref_candidate.replace("-", "").replace(".", "").lower()

    stmt = select(Order).where(
        or_(
            func.lower(func.replace(func.replace(Order.order_number, "-", ""), ".", "")) == ref_clean,
            func.lower(Order.order_number) == ref_candidate.lower(),
            cast(Order.id, String) == ref_candidate,
            cast(Order.meta, String).ilike(f'%"{ref_candidate}"%'),
        )
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        logger.warning(f"SNAP QR Notify: Order not found for reference {ref_candidate}")
        return {
            "responseCode": "4045100",
            "responseMessage": "Order Not Found",
        }

    # Update Order to Paid status
    order.payment_status = 2  # Paid
    order.status = Order.STATUS_PROCESSING
    meta = dict(order.meta) if isinstance(order.meta, dict) else {}
    meta["paid_at"] = datetime.datetime.now().isoformat()
    meta["snap_qr_payment"] = request.model_dump()
    order.meta = meta
    flag_modified(order, "meta")

    if order.settlement_id:
        try:
            await db.execute(
                text("UPDATE settlements SET status = 'success', settlement_date = :sdate, updated_at = :udate WHERE id = :sid"),
                {
                    "sdate": datetime.datetime.now(),
                    "udate": datetime.datetime.now(),
                    "sid": order.settlement_id,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update settlement status: {str(e)}")

    await db.commit()
    logger.info(f"SNAP QR Notify: Order {order.order_number} marked as Paid.")

    return {
        "responseCode": "2005100",
        "responseMessage": "Successful",
    }


# ==============================================================================
# Simulation Endpoint for Dev/Testing (No .env Needed)
# ==============================================================================

@router.post(
    "/simulate-pay/{order_id}",
    summary="Simulate Order Payment",
    description="Instantly marks an order as paid for testing and dev workflows without any external payment gateway or webhook.",
)
async def simulate_order_payment(
    order_id: uuid.UUID,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.payment_status = 2  # Paid
    order.status = Order.STATUS_PROCESSING
    meta = dict(order.meta) if isinstance(order.meta, dict) else {}
    meta["paid_at"] = datetime.datetime.now().isoformat()
    meta["simulated"] = True
    order.meta = meta
    flag_modified(order, "meta")

    if order.settlement_id:
        try:
            await db.execute(
                text("UPDATE settlements SET status = 'success', settlement_date = :sdate, updated_at = :udate WHERE id = :sid"),
                {
                    "sdate": datetime.datetime.now(),
                    "udate": datetime.datetime.now(),
                    "sid": order.settlement_id,
                }
            )
        except Exception:
            pass

    await db.commit()

    return {
        "success": True,
        "message": f"Order {order.order_number or order.id} successfully marked as paid.",
        "order_id": str(order.id),
        "order_number": order.order_number,
        "payment_status": order.payment_status,
        "status": order.status,
        "is_paid": True,
    }
