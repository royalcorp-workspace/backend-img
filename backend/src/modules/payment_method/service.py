from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import crud_payment_methods
from .schemas import PaymentMethodCreate, PaymentMethodRead, PaymentMethodUpdate

logger = get_logger()

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
    bank_info_or_pm: Any = None,
    pm_type: int | None = None,
    pm_name: str = "",
    bank_name: str = "",
) -> list[str]:
    """
    Resolve payment instructions (cara bayar) from bank_info or PaymentMethod if available,
    or provide structured instructions based on payment method type.
    """
    if hasattr(bank_info_or_pm, "bank_info"):  # PaymentMethod model or object instance
        pm = bank_info_or_pm
        info = pm.bank_info if isinstance(pm.bank_info, dict) else {}
        pm_type = pm.type if pm_type is None else pm_type
        pm_name = pm.name if not pm_name else pm_name
        bank_name = (
            bank_name
            or info.get("bank_name")
            or info.get("bank")
            or pm_name
        )
    elif isinstance(bank_info_or_pm, dict) and ("bank_info" in bank_info_or_pm or "code" in bank_info_or_pm):
        pm_dict = bank_info_or_pm
        info = pm_dict.get("bank_info") if isinstance(pm_dict.get("bank_info"), dict) else pm_dict
        pm_type = pm_dict.get("type") if pm_type is None else pm_type
        pm_name = pm_dict.get("name", "") if not pm_name else pm_name
        bank_name = (
            bank_name
            or info.get("bank_name")
            or info.get("bank")
            or pm_name
        )
    else:
        info = bank_info_or_pm if isinstance(bank_info_or_pm, dict) else {}
        bank_name = (
            bank_name
            or info.get("bank_name")
            or info.get("bank")
            or pm_name
        )

    # 1. Custom instructions from DB bank_info if available
    for key in ("cara_bayar", "instructions", "how_to_pay", "steps", "payment_instructions"):
        if key in info and info[key]:
            val = info[key]
            if isinstance(val, list):
                return [str(v) for v in val]
            elif isinstance(val, str):
                return [s.strip() for s in val.split("\n") if s.strip()]
            return [str(val)]

    # 2. Dynamic fallback instructions based on payment method type
    if pm_type == 1:  # VA (Virtual Account)
        return [
            f"Buka aplikasi Mobile Banking {bank_name} atau kunjungi ATM {bank_name} terdekat.",
            f"Pilih menu Transfer / Pembayaran > Virtual Account ({pm_name}).",
            "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
            "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
            "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
            "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
        ]
    elif pm_type == 2:  # Merchant / Retail (e.g. Indomaret, Alfamart)
        return [
            f"Kunjungi gerai {pm_name} terdekat (misal: Alfamart / Indomaret).",
            "Sampaikan kepada kasir bahwa Anda ingin melakukan pembayaran tagihan merchant.",
            "Tunjukkan kode pembayaran / nomor referensi kepada kasir.",
            "Lakukan pembayaran tunai / non-tunai sesuai total tagihan.",
            "Terima dan simpan struk pembayaran sebagai bukti transaksi yang sah.",
        ]
    elif pm_type == 3:  # E-Wallet (e.g. GoPay, OVO, ShopeePay, DANA)
        return [
            f"Buka aplikasi {pm_name} pada smartphone Anda.",
            "Pilih menu Bayar / Scan QR.",
            "Pastikan nama penerima dan nominal tagihan sesuai.",
            "Konfirmasi pembayaran dan masukkan PIN keamanan e-wallet Anda.",
            "Transaksi selesai dan status pesanan akan otomatis terverifikasi.",
        ]
    elif pm_type == 4:  # Credit Card
        return [
            "Masukkan informasi kartu kredit (Nomor Kartu, Masa Berlaku MM/YY, dan CVV).",
            "Klik tombol Proses Pembayaran.",
            "Masukkan kode OTP 3D-Secure yang dikirimkan ke nomor ponsel Anda.",
            "Tunggu notifikasi konfirmasi transaksi berhasil.",
        ]
    elif pm_type == 5:  # Bank Transfer
        return [
            f"Lakukan transfer ke rekening bank {bank_name} yang tertera.",
            "Pastikan nominal transfer sesuai persis hingga 3 digit terakhir.",
            "Simpan bukti transfer dan sistem akan otomatis memverifikasi pembayaran Anda.",
        ]
    elif pm_type == 6:  # QRIS
        return [
            "Buka aplikasi e-wallet atau mobile banking yang mendukung QRIS.",
            "Pilih menu Scan / Pindai QR.",
            "Arahkan kamera ke kode QRIS pembayaran.",
            "Periksa nominal dan nama merchant, lalu klik Bayar.",
            "Masukkan PIN untuk menyelesaikan transaksi.",
        ]
    elif pm_type == 7:  # Direct Debit
        return [
            f"Pilih akun Direct Debit {bank_name} Anda.",
            "Konfirmasi detail transaksi dan nomor ponsel terdaftar.",
            "Masukkan kode OTP yang dikirimkan via SMS.",
            "Pembayaran selesai seketika.",
        ]
    elif pm_type == 8:  # Paylater
        return [
            f"Login ke akun {pm_name} Anda.",
            "Pilih skema cicilan / periode pembayaran yang diinginkan.",
            "Periksa rincian tagihan bulanan dan bunga (jika ada).",
            "Konfirmasi transaksi dengan PIN atau OTP.",
        ]
    elif pm_type == 9:  # COD (Cash On Delivery)
        return [
            "Siapkan uang tunai sesuai total nominal belanjaan.",
            "Bayarkan uang tunai kepada kurir saat pesanan tiba di alamat tujuan.",
            "Periksa kondisi paket sebelum kurir meninggalkan lokasi.",
        ]
    else:
        return [
            f"Pilih metode pembayaran {pm_name}.",
            "Ikuti petunjuk pembayaran yang muncul pada halaman checkout.",
            "Selesaikan transaksi sebelum batas waktu yang ditentukan.",
            "Simpan bukti pembayaran Anda.",
        ]


def enrich_payment_method_data(item: dict[str, Any] | Any) -> dict[str, Any] | Any:
    """Enrich a payment method dict or model instance with bank_name, type_name, and cara_bayar."""
    if isinstance(item, dict):
        bank_info = item.get("bank_info") if isinstance(item.get("bank_info"), dict) else {}
        name = item.get("name", "")
        pm_type = item.get("type")
        bank_name = (
            bank_info.get("bank_name")
            or bank_info.get("bank")
            or name
        )
        type_name = resolve_payment_type_name(pm_type)
        cara_bayar = resolve_cara_bayar(bank_info, pm_type, name, bank_name)

        item["bank_name"] = bank_name
        item["type_name"] = type_name
        item["cara_bayar"] = cara_bayar
        return item
    elif hasattr(item, "__dict__"):
        bank_info = getattr(item, "bank_info", None)
        info_dict = bank_info if isinstance(bank_info, dict) else {}
        name = getattr(item, "name", "")
        pm_type = getattr(item, "type", None)
        bank_name = (
            info_dict.get("bank_name")
            or info_dict.get("bank")
            or name
        )
        type_name = resolve_payment_type_name(pm_type)
        cara_bayar = resolve_cara_bayar(info_dict, pm_type, name, bank_name)

        setattr(item, "bank_name", bank_name)
        setattr(item, "type_name", type_name)
        setattr(item, "cara_bayar", cara_bayar)
        return item
    return item


class PaymentMethodService:
    async def get_paginated(self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters):
        data = await crud_payment_methods.get_multi(
            db=db, offset=skip, limit=limit, schema_to_select=PaymentMethodRead, **filters
        )
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                enrich_payment_method_data(item)
        return data

    async def get_by_id(self, db: AsyncSession, method_id: UUID) -> dict[str, Any]:
        method = await crud_payment_methods.get(db=db, id=method_id, deleted=False)
        if not method:
            raise ResourceNotFoundError(f"Payment method with ID {method_id} not found")
        return enrich_payment_method_data(method)

    async def create(self, db: AsyncSession, method_in: PaymentMethodCreate) -> dict[str, Any]:
        existing = await crud_payment_methods.get(db=db, code=method_in.code)
        if existing:
            raise ResourceExistsError(f"Payment method with code '{method_in.code}' already exists")
        res = await crud_payment_methods.create(db=db, object=method_in)
        await db.commit()
        return enrich_payment_method_data(res)

    async def update(self, db: AsyncSession, method_id: UUID, method_in: PaymentMethodUpdate) -> dict[str, Any]:
        method = await crud_payment_methods.get(db=db, id=method_id, deleted=False)
        if not method:
            raise ResourceNotFoundError(f"Payment method with ID {method_id} not found")
        if method_in.code and method_in.code != method.get("code"):
            existing = await crud_payment_methods.get(db=db, code=method_in.code)
            if existing:
                raise ResourceExistsError(f"Payment method with code '{method_in.code}' already exists")
        res = await crud_payment_methods.update(db=db, object=method_in, id=method_id)
        await db.commit()
        return enrich_payment_method_data(res)

    async def delete(self, db: AsyncSession, method_id: UUID) -> None:
        method = await crud_payment_methods.get(db=db, id=method_id, deleted=False)
        if not method:
            raise ResourceNotFoundError(f"Payment method with ID {method_id} not found")
        await crud_payment_methods.delete(db=db, id=method_id)
        await db.commit()


payment_method_service = PaymentMethodService()
