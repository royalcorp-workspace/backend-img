from typing import Any, Annotated
import uuid
import hashlib
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.dependencies import AsyncSessionDep
from ..order.models import Order
from ..payment_method.models import PaymentMethod
from ..add_to_cart.models import AddToCart

router = APIRouter(prefix="/payment", tags=["Payment"])

ESPAY_SIGNATURE_KEY = "dummy_signature_key"  # Replace with actual from settings

# Payment method type mappings (1: VA, 2: Merchant, etc.)
PAYMENT_METHOD_TYPES: dict[int, str] = {
    1: "VA",
    2: "Merchant",
    3: "E-Wallet",
    4: "Credit Card",
    5: "Bank Transfer",
    6: "QRIS",
    7: "Direct Debit",
    8: "Paylater",
    9: "COD",
}


def resolve_payment_type_name(type_id: int | None) -> str | None:
    """Resolve payment method type ID to a human-readable name/label."""
    if type_id is None:
        return None
    return PAYMENT_METHOD_TYPES.get(type_id, f"Type {type_id}")


def resolve_cara_bayar(
    pm: PaymentMethod,
    bank_name: str,
    type_name: str | None,
) -> list[str]:
    """
    Resolve payment instructions (cara bayar) from bank_info if available,
    or provide structured instructions based on payment method type.
    """
    bank_info = pm.bank_info if isinstance(pm.bank_info, dict) else {}

    # 1. Custom instructions from DB bank_info if available
    for key in ("cara_bayar", "instructions", "how_to_pay", "steps", "payment_instructions"):
        if key in bank_info and bank_info[key]:
            val = bank_info[key]
            if isinstance(val, list):
                return [str(v) for v in val]
            elif isinstance(val, str):
                return [s.strip() for s in val.split("\n") if s.strip()]
            return [str(val)]

    # 2. Dynamic fallback instructions based on payment method type
    if pm.type == 1:  # VA (Virtual Account)
        return [
            f"Buka aplikasi Mobile Banking {bank_name} atau kunjungi ATM {bank_name} terdekat.",
            f"Pilih menu Transfer / Pembayaran > Virtual Account ({pm.name}).",
            "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
            "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
            "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
            "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
        ]
    elif pm.type == 2:  # Merchant / Retail (e.g. Indomaret, Alfamart)
        return [
            f"Kunjungi gerai {pm.name} terdekat (misal: Alfamart / Indomaret).",
            "Sampaikan kepada kasir bahwa Anda ingin melakukan pembayaran tagihan merchant.",
            "Tunjukkan kode pembayaran / nomor referensi kepada kasir.",
            "Lakukan pembayaran tunai / non-tunai sesuai total tagihan.",
            "Terima dan simpan struk pembayaran sebagai bukti transaksi yang sah.",
        ]
    elif pm.type == 3:  # E-Wallet (e.g. GoPay, OVO, ShopeePay, DANA)
        return [
            f"Buka aplikasi {pm.name} pada smartphone Anda.",
            "Pilih menu Bayar / Scan QR.",
            "Pastikan nama penerima dan nominal tagihan sesuai.",
            "Konfirmasi pembayaran dan masukkan PIN keamanan e-wallet Anda.",
            "Transaksi selesai dan status pesanan akan otomatis terverifikasi.",
        ]
    elif pm.type == 4:  # Credit Card
        return [
            "Masukkan informasi kartu kredit (Nomor Kartu, Masa Berlaku MM/YY, dan CVV).",
            "Klik tombol Proses Pembayaran.",
            "Masukkan kode OTP 3D-Secure yang dikirimkan ke nomor ponsel Anda.",
            "Tunggu notifikasi konfirmasi transaksi berhasil.",
        ]
    elif pm.type == 5:  # Bank Transfer
        return [
            f"Lakukan transfer ke rekening bank {bank_name} yang tertera.",
            "Pastikan nominal transfer sesuai persis hingga 3 digit terakhir.",
            "Simpan bukti transfer dan sistem akan otomatis memverifikasi pembayaran Anda.",
        ]
    elif pm.type == 6:  # QRIS
        return [
            "Buka aplikasi e-wallet atau mobile banking yang mendukung QRIS.",
            "Pilih menu Scan / Pindai QR.",
            "Arahkan kamera ke kode QRIS pembayaran.",
            "Periksa nominal dan nama merchant, lalu klik Bayar.",
            "Masukkan PIN untuk menyelesaikan transaksi.",
        ]
    elif pm.type == 7:  # Direct Debit
        return [
            f"Pilih akun Direct Debit {bank_name} Anda.",
            "Konfirmasi detail transaksi dan nomor ponsel terdaftar.",
            "Masukkan kode OTP yang dikirimkan via SMS.",
            "Pembayaran selesai seketika.",
        ]
    elif pm.type == 8:  # Paylater
        return [
            f"Login ke akun {pm.name} Anda.",
            "Pilih skema cicilan / periode pembayaran yang diinginkan.",
            "Periksa rincian tagihan bulanan dan bunga (jika ada).",
            "Konfirmasi transaksi dengan PIN atau OTP.",
        ]
    elif pm.type == 9:  # COD (Cash On Delivery)
        return [
            "Siapkan uang tunai sesuai total nominal belanjaan.",
            "Bayarkan uang tunai kepada kurir saat pesanan tiba di alamat tujuan.",
            "Periksa kondisi paket sebelum kurir meninggalkan lokasi.",
        ]
    else:
        return [
            f"Pilih metode pembayaran {pm.name}.",
            "Ikuti petunjuk pembayaran yang muncul pada halaman checkout.",
            "Selesaikan transaksi sebelum batas waktu yang ditentukan.",
            "Simpan bukti pembayaran Anda.",
        ]


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
    type: int | None = Field(None, example=1)
    type_name: str | None = Field(None, example="VA")
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
    cara_bayar: list[str] | None = Field(None)


class EspayPaymentData(BaseModel):
    id: str = Field(..., example="1a2b3c4d-5e6f-7g8h-9i0j-k1l2m3n4o5p6")
    order_id: str = Field(..., example="8f30c3a2-b911-4a4b-841a-e4b51a5c6d70")
    order_number: str | None = Field(None, example="ORD-20260828-001")
    payment_method: str = Field(..., example="BCAATM")
    bank_name: str | None = Field(None, example="BCA")
    type: int | None = Field(None, example=1)
    type_name: str | None = Field(None, example="VA")
    amount: float = Field(..., example=2500000.00)
    status: str = Field(..., example="pending")
    reference: str = Field(..., example="PAY-1724808000")
    payment_url: str = Field(..., example="https://sandbox-api.espay.id/checkout/8f30c3a2-b911-4a4b-841a-e4b51a5c6d70?bank=BCAATM")
    cara_bayar: list[str] | None = Field(None)
    payment_method_detail: PaymentMethodDetail | None = Field(None)


class EspayCheckoutResponse(BaseModel):
    success: bool = Field(..., example=True)
    payment: EspayPaymentData
    redirect_url: str = Field(..., example="https://sandbox-api.espay.id/checkout/8f30c3a2-b911-4a4b-841a-e4b51a5c6d70?bank=BCAATM")

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
                    "type": 1,
                    "type_name": "VA",
                    "amount": 2500000.00,
                    "status": "pending",
                    "reference": "PAY-1724808000",
                    "payment_url": "https://sandbox-api.espay.id/checkout/8f30c3a2-b911-4a4b-841a-e4b51a5c6d70?bank=BCAATM",
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
                        "type": 1,
                        "type_name": "VA",
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
                "redirect_url": "https://sandbox-api.espay.id/checkout/8f30c3a2-b911-4a4b-841a-e4b51a5c6d70?bank=BCAATM",
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
        "type": 1,
        "type_name": "VA",
        "amount": 2500000.00,
        "status": "pending",
        "reference": "PAY-1724808000",
        "payment_url": "https://sandbox-api.espay.id/checkout/8f30c3a2-b911-4a4b-841a-e4b51a5c6d70?bank=BCAATM",
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
            "type": 1,
            "type_name": "VA",
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
    "redirect_url": "https://sandbox-api.espay.id/checkout/8f30c3a2-b911-4a4b-841a-e4b51a5c6d70?bank=BCAATM",
}


@router.post(
    "/espay/checkout",
    response_model=EspayCheckoutResponse,
    summary="Espay Checkout",
    description="Initialize payment checkout via Espay with payment method details, instructions, bank name, and type.",
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
    stmt_order = select(Order).where(Order.id == request.order_id)
    result_order = await db.execute(stmt_order)
    order = result_order.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 2. Fetch Payment Method by code
    stmt_pm = select(PaymentMethod).where(
        PaymentMethod.code == request.payment_method_code,
        PaymentMethod.deleted == False,
    )
    result_pm = await db.execute(stmt_pm)
    payment_method = result_pm.scalar_one_or_none()

    if not payment_method:
        stmt_pm_any = select(PaymentMethod).where(PaymentMethod.code == request.payment_method_code)
        result_pm_any = await db.execute(stmt_pm_any)
        payment_method = result_pm_any.scalar_one_or_none()

    if not payment_method:
        raise HTTPException(
            status_code=404,
            detail=f"Payment method '{request.payment_method_code}' not found",
        )

    # 3. Update Order's selected payment method
    order.payment_method = payment_method.code

    # 4. Remove AddToCart if specific add_to_cart_id is provided in request or order.meta
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

    # 5. Resolve details (bank_name, type_name, cara_bayar)
    bank_info = payment_method.bank_info if isinstance(payment_method.bank_info, dict) else {}
    bank_name = (
        bank_info.get("bank_name")
        or bank_info.get("bank")
        or payment_method.name
    )
    type_name = resolve_payment_type_name(payment_method.type)
    cara_bayar = resolve_cara_bayar(payment_method, bank_name, type_name)

    amount = float(order.total)
    reference = f"PAY-{int(time.time())}"
    payment_url = f"https://sandbox-api.espay.id/checkout/{str(order.id)}?bank={payment_method.code}"

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
        "cara_bayar": cara_bayar,
    }

    payment_data = {
        "id": str(uuid.uuid4()),
        "order_id": str(order.id),
        "order_number": order.order_number,
        "payment_method": payment_method.code,
        "bank_name": bank_name,
        "type": payment_method.type,
        "type_name": type_name,
        "amount": amount,
        "status": "pending",
        "reference": reference,
        "payment_url": payment_url,
        "cara_bayar": cara_bayar,
        "payment_method_detail": payment_method_detail,
    }

    return {
        "success": True,
        "payment": payment_data,
        "redirect_url": payment_url,
    }


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

