from typing import Any
import uuid
import hashlib
import time
import datetime
import urllib.parse
import random
import re
import json
import hmac
import base64
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, String, cast, or_, text
from sqlalchemy.orm.attributes import flag_modified

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
    status: int = Field(..., example=3)
    is_paid: bool = Field(..., example=True)


class EspayCheckoutRequest(BaseModel):
    order_id: uuid.UUID = Field(..., example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    payment_method_code: str = Field(..., example="QRISPLUS", description="Payment method code, e.g. QRISPLUS, CREDITCARD, DEBITCARD")
    add_to_cart_id: uuid.UUID | None = Field(None, example="323e4567-e89b-12d3-a456-426614174002", description="Optional AddToCart ID to delete upon checkout")


class PaymentMethodDetail(BaseModel):
    id: uuid.UUID | str | None = Field(None, example="019f5933-08c8-7082-b1cd-7185cff32192")
    code: str = Field(..., example="QRISPLUS")
    name: str = Field(..., example="Qris Plus")
    type: int | None = Field(None, example=4)
    type_name: str | None = Field(None, example="QRIS")
    bank_name: str | None = Field(None, example="Qris Plus")
    provider: str | None = Field(None, example="espay")
    image: str | None = Field(None, example="https://example.com/qris.png")
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
    trx_id: str | None = Field(None, example="TRX-QRIS-20260828001-1234", description="Unique transaction ID / reference")
    settlement_id: str | None = Field(None, example="01a01e2f-814e-7325-bc2a-347096fb92c2", description="Linked settlements table ID")
    payment_method: str = Field(..., example="QRISPLUS")
    bank_name: str | None = Field(None, example="Qris Plus")
    type: int | None = Field(None, example=4)
    type_name: str | None = Field(None, example="QRIS")
    amount: float = Field(..., example=2500000.00)
    status: str = Field(..., example="pending")
    reference: str = Field(..., example="TRX-QRIS-20260828001-1234")
    payment_url: str = Field(..., example="/thankyou?order_id=8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    qr_string: str | None = Field(None, example="ID.CO.QRIS.IMG.ORD001.250000")
    qr_code: str | None = Field(None, example="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=...")
    va_number: str | None = Field(None, example=None)
    va_expired: str | None = Field(None, example="2026-09-02 10:00:00")
    cara_bayar: list[str] | None = Field(None)
    payment_method_detail: PaymentMethodDetail | None = Field(None)


class EspayCheckoutResponse(BaseModel):
    success: bool = Field(..., example=True)
    payment: dict[str, Any] | EspayPaymentData
    redirect_url: str = Field(..., example="/thankyou?order_id=8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    trx_id: str | None = Field(None, example="TRX-QRIS-20260828001-1234")
    settlement_id: str | None = Field(None, example="01a01e2f-814e-7325-bc2a-347096fb92c2")
    qr_string: str | None = Field(None, example="ID.CO.QRIS.IMG.ORD001.250000")
    qr_code: str | None = Field(None, example="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=...")
    va_number: str | None = Field(None, example=None)
    va_expired: str | None = Field(None, example="2026-09-02 10:00:00")


# Notification Schemas (QRIS & Cards)
class SnapAmount(BaseModel):
    value: str = Field(..., example="2500000.00")
    currency: str = Field("IDR", example="IDR")


class QrisNotifyRequest(BaseModel):
    partnerReferenceNo: str | None = Field(None, example="ORD-20260828-001")
    originalPartnerReferenceNo: str | None = None
    referenceNo: str | None = None
    trxId: str | None = None
    order_id: str | None = None
    amount: SnapAmount | dict[str, Any] | None = None
    additionalInfo: dict[str, Any] | None = None


class CardNotifyRequest(BaseModel):
    order_id: str | None = Field(None, example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    order_number: str | None = Field(None, example="ORD.20261008.0006")
    transaction_id: str | None = Field(None, example="TRX-CC-1724808000")
    reference_no: str | None = None
    trx_id: str | None = None
    masked_card: str | None = Field(None, example="411111******1111")
    card_type: str | None = Field(None, example="CREDIT", description="CREDIT or DEBIT")
    bank: str | None = Field(None, example="BCA")
    approval_code: str | None = Field(None, example="123456")
    status: str | None = Field(None, example="SUCCESS")
    amount: float | str | None = None
    additional_info: dict[str, Any] | None = None


# ==============================================================================
# Helpers
# ==============================================================================

def resolve_espay_product_code(
    code_or_bank: str | None,
    payment_type: int | None = None,
    bank_info: dict[str, Any] | None = None,
    payment_method_code: str | None = None,
) -> str:
    """Resolves Espay product code for QRIS, Credit Card, Debit Card, etc."""
    if bank_info and isinstance(bank_info, dict):
        p_code = bank_info.get("product_code")
        if p_code and str(p_code).strip() and not str(p_code).strip().isdigit():
            return str(p_code).strip().upper()

    candidate = (payment_method_code or code_or_bank or "").strip()
    if candidate and not candidate.isdigit():
        return candidate.upper()

    bank_code = (code_or_bank or (bank_info.get("bank_code") if isinstance(bank_info, dict) else "") or "").strip()

    BANK_PRODUCT_MAP: dict[str, dict[Any, str]] = {
        "008": {
            4: "QRISPLUS",
            5: "CREDITCARD",
            6: "DEBITCARD",
            "default": "QRISPLUS",
        },
        "014": {
            5: "CREDITCARD",
            6: "DEBITCARD",
            "default": "BCAATM",
        },
    }

    if bank_code in BANK_PRODUCT_MAP:
        mapping = BANK_PRODUCT_MAP[bank_code]
        if payment_type and payment_type in mapping:
            return mapping[payment_type]
        return mapping.get("default", bank_code)

    return candidate or bank_code


def get_default_instructions_for_method(code_upper: str, pm_type: int | None) -> list[str]:
    """Default instructions tailored for QRIS, Credit Card, and Debit Card."""
    if pm_type == 4 or "QRIS" in code_upper:
        return [
            "Buka aplikasi Mobile Banking atau E-Wallet (BCA Mobile, Livin, GoPay, OVO, Dana, ShopeePay, dll).",
            "Pilih menu 'Scan QR' atau 'Bayar dengan QRIS'.",
            "Arahkan kamera ke kode QRIS di atas atau unggah gambar QRIS yang telah diunduh.",
            "Periksa detail merchant dan pastikan total tagihan sesuai.",
            "Masukkan PIN transaksi Anda untuk menyelesaikan pembayaran.",
            "Pembayaran akan otomatis terkonfirmasi secara instan.",
        ]
    elif pm_type == 5 or "CREDIT" in code_upper:
        return [
            "Masukkan 16 digit Nomor Kartu Kredit Visa / Mastercard / JCB Anda.",
            "Masukkan Masa Berlaku kartu (Bulan dan Tahun / MM/YY).",
            "Masukkan 3 digit kode keamanan CVV/CVC yang tertera di bagian belakang kartu.",
            "Klik tombol Bayar Sekarang untuk memproses verifikasi 3D Secure.",
            "Masukkan kode OTP yang dikirimkan oleh bank melalui SMS ke nomor handphone Anda.",
            "Transaksi selesai setelah proses otorisasi berhasil.",
        ]
    elif pm_type == 6 or "DEBIT" in code_upper:
        return [
            "Pastikan fitur Transaksi Debit Online / E-Commerce kartu debit Anda telah aktif via Mobile Banking.",
            "Masukkan 16 digit Nomor Kartu Debit Anda.",
            "Masukkan Masa Berlaku kartu (MM/YY) dan 3 digit CVV di belakang kartu.",
            "Klik tombol Bayar Sekarang.",
            "Masukkan kode verifikasi OTP yang dikirimkan oleh bank melalui SMS.",
            "Pembayaran selesai secara langsung setelah verifikasi kode OTP berhasil.",
        ]
    return [
        "Selesaikan pembayaran sesuai metode yang dipilih.",
        "Simpan bukti pembayaran Anda.",
    ]


def generate_native_payment_details(
    order: Order,
    payment_method: PaymentMethod,
    bank_code: str,
) -> dict[str, Any]:
    """
    Generates native payment details with an explicit unique TRX ID for QRIS,
    Debit Card, Credit Card, and others without requiring external Espay credentials in .env.
    """
    code_upper = (payment_method.code or "").upper()
    pm_type = payment_method.type
    clean_order_ref = (order.order_number or str(order.id)[:8]).replace("-", "").replace(".", "")
    random_suffix = random.randint(1000, 9999)

    now = datetime.datetime.now()
    va_expired = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    qr_string = None
    qr_code = None
    va_number = None

    is_qris = (pm_type == 4)
    is_credit_card = (pm_type == 5)
    is_debit_card = (pm_type == 6)

    if is_qris:
        trx_id = f"TRX-QRIS-{clean_order_ref}-{random_suffix}"
        qr_string = f"ID.CO.QRIS.IMG.{clean_order_ref}.{round(float(order.total or 0))}"
        qr_code = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(qr_string)}"
        va_number = None
        payment_url = f"/thankyou?order_id={order.id}"
    elif is_credit_card:
        trx_id = f"TRX-CC-{clean_order_ref}-{random_suffix}"
        payment_url = f"/checkout/card-pay?order_id={order.id}&method=credit_card"
    elif is_debit_card:
        trx_id = f"TRX-DC-{clean_order_ref}-{random_suffix}"
        payment_url = f"/checkout/card-pay?order_id={order.id}&method=debit_card"
    else:
        order_digits = "".join([c for c in clean_order_ref if c.isdigit()])
        if len(order_digits) < 6:
            order_digits = f"{order_digits}{random.randint(100000, 999999)}"
        va_number = f"88{order_digits[-8:]}"
        trx_id = f"TRX-VA-{va_number}-{random_suffix}"
        payment_url = f"/thankyou?order_id={order.id}"

    return {
        "trx_id": trx_id,
        "reference": trx_id,
        "va_number": va_number,
        "va_expired": va_expired if va_number else None,
        "qr_string": qr_string,
        "qr_code": qr_code,
        "payment_url": payment_url,
    }


# ==============================================================================
# Checkout Endpoints
# ==============================================================================

@router.post(
    "/checkout",
    response_model=dict[str, Any],
    summary="Checkout Payment (QRIS, Debit, Credit Card)",
    description="Initiates payment checkout, saves trx_id and payment identifiers in order.meta and settlements table.",
)
@router.post(
    "/espay/checkout",
    response_model=dict[str, Any],
    summary="Checkout Payment (Alias)",
    description="Alias endpoint for checkout initialization.",
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

    # 2. Fetch Payment Method
    pm_code_input = request.payment_method_code.strip()
    pm_stmt = select(PaymentMethod).where(
        func.upper(PaymentMethod.code) == pm_code_input.upper(),
        PaymentMethod.deleted == False,
    )
    pm_result = await db.execute(pm_stmt)
    payment_method = pm_result.scalar_one_or_none()

    if not payment_method:
        escalated_code = resolve_espay_product_code(pm_code_input)
        if escalated_code != pm_code_input:
            pm_stmt_esc = select(PaymentMethod).where(
                func.upper(PaymentMethod.code) == escalated_code.upper(),
                PaymentMethod.deleted == False,
            )
            pm_result_esc = await db.execute(pm_stmt_esc)
            payment_method = pm_result_esc.scalar_one_or_none()

    if not payment_method:
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

    # 3. Resolve details & instructions
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
    if not cara_bayar or len(cara_bayar) == 0:
        cara_bayar = get_default_instructions_for_method(payment_method.code, payment_method.type)

    espay_bank_code = resolve_espay_product_code(
        code_or_bank=request.payment_method_code,
        payment_type=payment_method.type,
        bank_info=bank_info,
        payment_method_code=payment_method.code,
    )

    # 4. Check Espay Credentials or Generate Native Details
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
    clean_order_ref = (order.order_number or str(order.id)[:8]).replace("-", "").replace(".", "")
    trx_id = f"TRX-IMG-{clean_order_ref}-{random.randint(1000, 9999)}"
    reference = trx_id
    payment_url = f"/thankyou?order_id={order.id}"
    espay_success = False

    if has_espay_env:
        try:
            amount = f"{float(order.total or 0.0):.2f}"
            base_url = settings.ESPAY_BASE_URL.rstrip('/')

            if payment_method.type == 4:
                # =========================================================================
                # SNAP QRIS MPM Integration (Direct API SNAP)
                # Menghindari bentrok bank_code 008 (Mandiri VA)
                # =========================================================================
                snap_qr_url = re.sub(r'/rest/.*$', '', base_url) + '/api/v1.0/qr/qr-mpm-generate'
                partner_ref = order.order_number.replace("-", "").replace(".", "") if order.order_number else str(order.id).replace("-", "")
                qris_product_code = "SALDOMUQR"
                if isinstance(payment_method.bank_info, dict) and payment_method.bank_info.get("product_code"):
                    qris_product_code = payment_method.bank_info["product_code"]

                validity_period = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+07:00")
                qris_payload = {
                    "partnerReferenceNo": partner_ref,
                    "merchantId": settings.ESPAY_MERCHANT_KEY,
                    "amount": {
                        "value": amount,
                        "currency": "IDR",
                    },
                    "additionalInfo": {
                        "productCode": qris_product_code,
                    },
                    "validityPeriod": validity_period,
                }

                x_timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
                x_external_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
                json_str = json.dumps(qris_payload, separators=(',', ':'))
                body_hash = hashlib.sha256(json_str.encode()).hexdigest().lower()
                string_to_sign = f"POST:/api/v1.0/qr/qr-mpm-generate:{body_hash}:{x_timestamp}"

                x_sig = base64.b64encode(
                    hmac.new(settings.ESPAY_SIGNATURE_KEY.encode(), string_to_sign.encode(), hashlib.sha512).digest()
                ).decode()

                headers = {
                    "Content-Type": "application/json",
                    "X-TIMESTAMP": x_timestamp,
                    "X-SIGNATURE": x_sig,
                    "X-EXTERNAL-ID": x_external_id,
                    "X-PARTNER-ID": settings.ESPAY_MERCHANT_KEY,
                    "CHANNEL-ID": "ESPAY",
                }

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(snap_qr_url, json=qris_payload, headers=headers)
                    payment_data = response.json()

                if response.status_code == 200 and (payment_data.get('responseCode') in ('2004700', '2000000') or payment_data.get('error_code') == '0000'):
                    va_number = None
                    va_expired = None
                    add_info = payment_data.get('additionalInfo') if isinstance(payment_data.get('additionalInfo'), dict) else {}
                    trx_id = (
                        add_info.get('referenceNo')
                        or payment_data.get('referenceNo')
                        or payment_data.get('trx_id')
                    )
                    if not trx_id and payment_data.get('qrUrl'):
                        parsed = urllib.parse.urlparse(payment_data.get('qrUrl'))
                        query_params = urllib.parse.parse_qs(parsed.query)
                        if 'trx_id' in query_params:
                            trx_id = query_params['trx_id'][0]
                    trx_id = trx_id or f"TRX-QRIS-{clean_order_ref}-{random.randint(1000, 9999)}"
                    reference = trx_id
                    qr_string = payment_data.get('qrContent') or payment_data.get('qr_string')
                    qr_code = payment_data.get('qrImage') or payment_data.get('qrUrl') or payment_data.get('qr_code')
                    payment_url = f"/thankyou?order_id={order.id}"
                    espay_success = True
                    logger.info(f"SNAP QRIS MPM succeeded for order {order.order_number}, TRX ID: {trx_id}")
                else:
                    logger.warning(f"SNAP QRIS MPM unfulfilled, falling back to native generator. Response: {payment_data}")
            elif payment_method.type == 6:
                # =========================================================================
                # Direct Debit Integration
                # Sesuai Spesifikasi Request Direct Debit Espay
                # =========================================================================
                debit_url = re.sub(r'/rest/.*$', '', base_url) + '/apidirectdebit/v1.0/debit/registration-account-binding'
                clean_order_ref = re.sub(r'[^\d]', '', order.order_number) if order.order_number else str(order.id)[:12]
                if len(clean_order_ref) < 8:
                    clean_order_ref = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
                partner_reference_no = clean_order_ref

                debit_phone = "087888888888"
                cust_name = "Customer"
                debit_product_code = "DANAMONDIRECTDEBIT"
                if isinstance(payment_method.bank_info, dict) and payment_method.bank_info.get("product_code"):
                    debit_product_code = payment_method.bank_info["product_code"]

                account_token = f"ESP{datetime.datetime.now().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:16]}"
                cust_account_no = clean_order_ref[-12:]

                debit_payload = {
                    "partnerReferenceNo": partner_reference_no,
                    "merchantId": settings.ESPAY_MERCHANT_KEY,
                    "phoneNo": debit_phone,
                    "authCode": "YT1Ex4UGXzAcxw5Ve8l4QNLH2GmGPN",
                    "additionalInfo": {
                        "productCode": debit_product_code,
                        "accountToken": account_token,
                        "ktpFile": "",
                        "npwpFile": "",
                        "pdfFile": "",
                        "amount": {
                            "value": amount,
                            "currency": "IDR",
                        },
                        "customerAccountNumber": cust_account_no,
                        "customerName": cust_name,
                        "debitType": "V",
                    },
                }

                x_timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
                x_external_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))
                json_str = json.dumps(debit_payload, separators=(',', ':'))
                body_hash = hashlib.sha256(json_str.encode()).hexdigest().lower()
                string_to_sign = f"POST:/apidirectdebit/v1.0/debit/registration-account-binding:{body_hash}:{x_timestamp}"

                x_sig = base64.b64encode(
                    hmac.new(settings.ESPAY_SIGNATURE_KEY.encode(), string_to_sign.encode(), hashlib.sha512).digest()
                ).decode()

                headers = {
                    "Content-Type": "application/json",
                    "X-TIMESTAMP": x_timestamp,
                    "X-SIGNATURE": x_sig,
                    "X-EXTERNAL-ID": x_external_id,
                    "X-PARTNER-ID": settings.ESPAY_MERCHANT_KEY,
                    "CHANNEL-ID": "ESPAY",
                }

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(debit_url, json=debit_payload, headers=headers)
                    payment_data = response.json()

                if response.status_code == 200 and (payment_data.get('responseCode') in ('2005400', '2005500', '2000000') or payment_data.get('error_code') == '0000'):
                    va_number = None
                    va_expired = None
                    add_info = payment_data.get('additionalInfo') if isinstance(payment_data.get('additionalInfo'), dict) else {}
                    trx_id = (
                        add_info.get('referenceNo')
                        or payment_data.get('referenceNo')
                        or payment_data.get('trx_id')
                        or f"TRX-DC-{clean_order_ref}-{random.randint(1000, 9999)}"
                    )
                    reference = trx_id
                    payment_url = payment_data.get('webRedirectUrl') or payment_data.get('payment_url') or payment_url
                    espay_success = True
                    logger.info(f"Direct Debit registration succeeded for order {order.order_number}, TRX ID: {trx_id}")
                else:
                    logger.warning(f"Direct Debit unfulfilled, falling back to native generator. Response: {payment_data}")
            else:
                # =========================================================================
                # Standard Virtual Account & SendInvoice Integration (TETAP UTUH)
                # =========================================================================
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

                    additional_info = payment_data.get('additionalInfo') if isinstance(payment_data.get('additionalInfo'), dict) else {}
                    trx_id = (
                        payment_data.get('trx_id')
                        or payment_data.get('referenceNo')
                        or additional_info.get('referenceNo')
                        or payment_data.get('reference')
                        or reference
                    )
                    reference = trx_id
                    payment_url = payment_data.get('payment_url', payment_url)
                    espay_success = True
                    logger.info(f"Espay SendInvoice succeeded for order {order.order_number}, TRX ID: {trx_id}")
                else:
                    logger.warning(f"Espay SendInvoice unfulfilled. Falling back to native payment generator.")
        except Exception as e:
            logger.warning(f"Espay API connection exception: {str(e)}. Falling back to native payment generator.")

    if not espay_success:
        logger.info(f"Using IMG native payment generator for {payment_method.code} (Order {order.order_number or order.id})")
        native_details = generate_native_payment_details(order, payment_method, espay_bank_code)
        trx_id = native_details["trx_id"]
        reference = native_details["reference"]
        va_number = native_details["va_number"]
        va_expired = native_details["va_expired"]
        qr_string = native_details["qr_string"]
        qr_code = native_details["qr_code"]
        payment_url = native_details["payment_url"]

    # 5. Record / Update Settlement in database table 'settlements'
    settlement_id = order.settlement_id
    try:
        settlement_ref = order.order_number or str(order.id)
        settlement_res = await db.execute(
            text(
                """
                INSERT INTO settlements (id, reference_id, gross_amount, fee_amount, net_amount, status, notes, created_at, updated_at)
                VALUES (gen_random_uuid(), :ref_id, :gross, :fee, :net, 'pending', :notes, NOW(), NOW())
                ON CONFLICT (reference_id) DO UPDATE SET
                    gross_amount = EXCLUDED.gross_amount,
                    fee_amount = EXCLUDED.fee_amount,
                    net_amount = EXCLUDED.net_amount,
                    notes = EXCLUDED.notes,
                    updated_at = NOW()
                RETURNING id;
                """
            ),
            {
                "ref_id": settlement_ref,
                "gross": float(order.total or 0.0),
                "fee": float(order.transaction_fee or 0.0),
                "net": float(order.total or 0.0),
                "notes": f"Payment via {payment_method.code} (TRX ID: {trx_id})",
            },
        )
        settlement_id = settlement_res.scalar()
    except Exception as e:
        logger.warning(f"Failed to upsert settlement record: {str(e)}")

    # 6. Update Order in DB
    order.payment_method = payment_method.code
    order.payment_status = 1  # Pending
    if settlement_id:
        order.settlement_id = settlement_id

    # Store all transaction codes (trx_id, va_number, qr_string, references) cleanly in order.meta
    meta = dict(order.meta) if isinstance(order.meta, dict) else {}
    meta['trx_id'] = trx_id
    meta['reference'] = reference
    meta['espay_reference'] = reference
    meta['payment_method_code'] = payment_method.code
    meta['payment_method_type'] = payment_method.type
    meta['settlement_id'] = str(settlement_id) if settlement_id else None
    if va_number:
        meta['va_number'] = va_number
        meta['va_expired'] = va_expired
    if qr_string:
        meta['qr_string'] = qr_string
        meta['qr_code'] = qr_code
    order.meta = meta
    flag_modified(order, "meta")

    # 7. Clean up AddToCart if requested
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
        "trx_id": trx_id,
        "settlement_id": str(settlement_id) if settlement_id else None,
        "payment_method": payment_method.code,
        "bank_name": bank_name,
        "type": payment_method.type,
        "type_name": type_name,
        "amount": float(order.total or 0.0),
        "status": "pending",
        "reference": reference,
        "payment_url": payment_url,
        "cara_bayar": cara_bayar,
        "qr_string": qr_string,
        "qr_code": qr_code,
        "va_number": va_number,
        "va_expired": va_expired,
        "payment_method_detail": payment_method_detail,
    }

    return {
        "success": True,
        "payment": payment_result,
        "redirect_url": payment_url,
        "trx_id": trx_id,
        "settlement_id": str(settlement_id) if settlement_id else None,
        "qr_string": qr_string,
        "qr_code": qr_code,
        "va_number": va_number,
        "va_expired": va_expired,
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
    summary="Check Payment Status (Alias)",
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
# QRIS Callback & Webhook Endpoints
# ==============================================================================

@router.post(
    "/qris/notify",
    summary="QRIS Payment Notification",
    description="Callback/webhook endpoint for QRIS payment completion.",
)
@router.post(
    "/snap/qr-notify",
    summary="QRIS Payment Notification (SNAP Path)",
    description="SNAP BI path for QRIS payment completion.",
)
@router.post(
    "/v1.0/qr/qr-mpm-notify",
    summary="QRIS Payment Notification (BI Standard Path)",
    description="Bank Indonesia SNAP QR MPM payment notification.",
)
async def qris_payment_notification(
    request: QrisNotifyRequest,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    ref_candidate = (
        request.partnerReferenceNo
        or request.originalPartnerReferenceNo
        or request.referenceNo
        or request.trxId
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
        logger.warning(f"QRIS Notification: Order not found for reference '{ref_candidate}'")
        return {
            "responseCode": "4045100",
            "responseMessage": "Order Not Found",
        }

    # Mark as Paid
    order.payment_status = 2  # Paid
    order.status = Order.STATUS_PROCESSING  # 3: Diproses
    meta = dict(order.meta) if isinstance(order.meta, dict) else {}
    meta["paid_at"] = datetime.datetime.now().isoformat()
    meta["qris_payment_notification"] = request.model_dump()
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
    logger.info(f"QRIS Payment verified for Order {order.order_number}")

    return {
        "responseCode": "2005100",
        "responseMessage": "Successful",
        "order_id": str(order.id),
        "order_number": order.order_number,
        "trx_id": meta.get("trx_id"),
        "status": "PAID",
    }


# ==============================================================================
# Credit Card & Debit Card Callback & Webhook Endpoints
# ==============================================================================

@router.post(
    "/card/notify",
    summary="Debit & Credit Card Payment Notification",
    description="Callback/webhook endpoint for Debit Card and Credit Card transaction authorization & settlement.",
)
@router.post(
    "/card/callback",
    summary="Card Payment Callback (Alias)",
    description="Alias endpoint for card payment notification.",
)
async def card_payment_notification(
    request: CardNotifyRequest,
    db: AsyncSessionDep,
) -> dict[str, Any]:
    ref_candidate = (
        request.order_number
        or request.order_id
        or request.reference_no
        or request.transaction_id
        or request.trx_id
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
        logger.warning(f"Card Notification: Order not found for reference '{ref_candidate}'")
        return {
            "success": False,
            "message": "Order Not Found",
        }

    # Mark as Paid
    order.payment_status = 2  # Paid
    order.status = Order.STATUS_PROCESSING  # 3: Diproses
    meta = dict(order.meta) if isinstance(order.meta, dict) else {}
    meta["paid_at"] = datetime.datetime.now().isoformat()
    meta["card_payment_notification"] = request.model_dump()
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
    logger.info(f"Card Payment ({request.card_type or 'CARD'}) verified for Order {order.order_number}")

    return {
        "success": True,
        "message": "Card payment processed successfully",
        "order_id": str(order.id),
        "order_number": order.order_number,
        "trx_id": meta.get("trx_id"),
        "status": "PAID",
        "card_type": request.card_type,
        "masked_card": request.masked_card,
    }


# ==============================================================================
# Simulation Endpoint for Dev/Testing (No .env Needed)
# ==============================================================================

@router.post(
    "/simulate-pay/{order_id}",
    summary="Simulate Order Payment (Dev/Testing)",
    description="Instantly marks an order as paid for testing QRIS, Debit, or Credit Card workflows without external webhooks.",
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
        "trx_id": meta.get("trx_id"),
        "payment_status": order.payment_status,
        "status": order.status,
        "is_paid": True,
    }
