import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.logging import get_logger
from ..common.exceptions import ResourceExistsError, ResourceNotFoundError
from .crud import crud_payment_methods
from .schemas import PaymentMethodCreate, PaymentMethodRead, PaymentMethodUpdate

logger = get_logger()

PAYMENT_METHOD_TYPES: dict[int, str] = {
    1: "Bank Transfer",
    2: "Virtual Account",
    3: "E-Wallet",
    4: "QRIS",
    5: "Credit Card",
    6: "Debit Card",
    7: "COD",
    8: "PayLater",
}


def resolve_payment_type_name(type_id: int | None) -> str | None:
    """Resolve payment method type ID to a human-readable name/label."""
    if type_id is None:
        return None
    return PAYMENT_METHOD_TYPES.get(type_id, "Unknown")


def _parse_instructions_json(raw_instructions: Any) -> list[str] | None:
    """Helper to parse instructions column data (JSON list, dict, or string)."""
    if raw_instructions is None:
        return None

    if isinstance(raw_instructions, str):
        raw_str = raw_instructions.strip()
        if (raw_str.startswith("[") and raw_str.endswith("]")) or (raw_str.startswith("{") and raw_str.endswith("}")):
            try:
                parsed = json.loads(raw_str)
                return _parse_instructions_json(parsed)
            except Exception:
                pass
        # Plain multiline string
        lines = [line.strip() for line in raw_str.split("\n") if line.strip()]
        return lines if lines else None

    if isinstance(raw_instructions, list):
        items = []
        for item in raw_instructions:
            if isinstance(item, str) and item.strip():
                items.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("instruction") or item.get("step") or item.get("desc")
                if text:
                    items.append(str(text))
                else:
                    items.append(str(item))
            elif item is not None:
                items.append(str(item))
        return items if items else None

    if isinstance(raw_instructions, dict):
        # 1. Check common direct keys
        for key in ("cara_bayar", "instructions", "steps", "how_to_pay", "payment_instructions", "data", "list"):
            if key in raw_instructions and raw_instructions[key]:
                res = _parse_instructions_json(raw_instructions[key])
                if res:
                    return res
        # 2. If it has grouped keys like {"atm": [...], "m_banking": [...]}
        grouped_items = []
        for group_name, steps in raw_instructions.items():
            if isinstance(steps, list):
                header = group_name.replace("_", " ").title()
                grouped_items.append(f"[{header}]")
                for s in steps:
                    grouped_items.append(str(s))
            elif isinstance(steps, str) and steps.strip():
                grouped_items.append(f"[{group_name}]: {steps.strip()}")
        if grouped_items:
            return grouped_items

    return None


def resolve_cara_bayar(
    bank_info_or_pm: Any = None,
    pm_type: int | None = None,
    pm_name: str = "",
    bank_name: str = "",
    instructions: Any = None,
) -> list[str]:
    """
    Resolve payment instructions (cara bayar) from instructions column,
    bank_info, or provide structured instructions based on payment method type.
    """
    custom_instructions = instructions

    if hasattr(bank_info_or_pm, "bank_info") or hasattr(bank_info_or_pm, "instructions"):  # PaymentMethod model
        pm = bank_info_or_pm
        info = pm.bank_info if isinstance(pm.bank_info, dict) else {}
        if custom_instructions is None:
            custom_instructions = getattr(pm, "instructions", None)
        pm_type = pm.type if pm_type is None else pm_type
        pm_name = pm.name if not pm_name else pm_name
        bank_name = (
            bank_name
            or info.get("bank_name")
            or info.get("bank")
            or pm_name
        )
    elif isinstance(bank_info_or_pm, dict) and ("bank_info" in bank_info_or_pm or "instructions" in bank_info_or_pm or "code" in bank_info_or_pm):
        pm_dict = bank_info_or_pm
        info = pm_dict.get("bank_info") if isinstance(pm_dict.get("bank_info"), dict) else pm_dict
        if custom_instructions is None:
            custom_instructions = pm_dict.get("instructions")
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

    # 1. Primary: Parse from instructions column (JSON / list / dict)
    parsed_instructions = _parse_instructions_json(custom_instructions)
    if parsed_instructions:
        return parsed_instructions

    # 2. Fallback: Parse from bank_info if available
    for key in ("cara_bayar", "instructions", "how_to_pay", "steps", "payment_instructions"):
        if key in info and info[key]:
            parsed = _parse_instructions_json(info[key])
            if parsed:
                return parsed

    # 3. Dynamic fallback instructions based on payment method type
    if pm_type == 1:  # Bank Transfer
        return [
            f"Lakukan transfer ke rekening bank {bank_name} yang tertera.",
            "Pastikan nominal transfer sesuai persis hingga 3 digit terakhir.",
            "Simpan bukti transfer dan sistem akan otomatis memverifikasi pembayaran Anda.",
        ]
    elif pm_type == 2:  # Virtual Account
        return [
            f"Buka aplikasi Mobile Banking {bank_name} atau kunjungi ATM {bank_name} terdekat.",
            f"Pilih menu Transfer / Pembayaran > Virtual Account ({pm_name}).",
            "Masukkan nomor Virtual Account tujuan pembayaran yang tertera.",
            "Periksa kecocokan nama penerima dan nominal tagihan transaksi Anda.",
            "Konfirmasi transaksi dan masukkan PIN untuk menyelesaikan pembayaran.",
            "Simpan bukti pembayaran atau struk transfer sebagai bukti sah.",
        ]
    elif pm_type == 3:  # E-Wallet
        return [
            f"Buka aplikasi {pm_name} pada smartphone Anda.",
            "Pilih menu Bayar / Scan QR.",
            "Pastikan nama penerima dan nominal tagihan sesuai.",
            "Konfirmasi pembayaran dan masukkan PIN keamanan e-wallet Anda.",
            "Transaksi selesai dan status pesanan akan otomatis terverifikasi.",
        ]
    elif pm_type == 4:  # QRIS
        return [
            "Buka aplikasi e-wallet atau mobile banking yang mendukung QRIS.",
            "Pilih menu Scan / Pindai QR.",
            "Arahkan kamera ke kode QRIS pembayaran.",
            "Periksa nominal dan nama merchant, lalu klik Bayar.",
            "Masukkan PIN untuk menyelesaikan transaksi.",
        ]
    elif pm_type == 5:  # Credit Card
        return [
            "Masukkan informasi kartu kredit (Nomor Kartu, Masa Berlaku MM/YY, dan CVV).",
            "Klik tombol Proses Pembayaran.",
            "Masukkan kode OTP 3D-Secure yang dikirimkan ke nomor ponsel Anda.",
            "Tunggu notifikasi konfirmasi transaksi berhasil.",
        ]
    elif pm_type == 6:  # Debit Card
        return [
            f"Pilih pembayaran Debit Online / Debit Card {bank_name}.",
            "Masukkan nomor kartu debit, tanggal kadaluarsa, dan CVV.",
            "Masukkan kode OTP yang dikirimkan via SMS.",
            "Pembayaran selesai seketika.",
        ]
    elif pm_type == 7:  # COD
        return [
            "Siapkan uang tunai sesuai total nominal belanjaan.",
            "Bayarkan uang tunai kepada kurir saat pesanan tiba di alamat tujuan.",
            "Periksa kondisi paket sebelum kurir meninggalkan lokasi.",
        ]
    elif pm_type == 8:  # PayLater
        return [
            f"Login ke akun {pm_name} Anda.",
            "Pilih skema cicilan / periode pembayaran yang diinginkan.",
            "Periksa rincian tagihan bulanan dan bunga (jika ada).",
            "Konfirmasi transaksi dengan PIN atau OTP.",
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
        instructions = item.get("instructions")
        name = item.get("name", "")
        pm_type = item.get("type")
        bank_name = (
            bank_info.get("bank_name")
            or bank_info.get("bank")
            or name
        )
        type_name = resolve_payment_type_name(pm_type)
        cara_bayar = resolve_cara_bayar(item, pm_type, name, bank_name, instructions=instructions)

        item["bank_name"] = bank_name
        item["type_name"] = type_name
        item["cara_bayar"] = cara_bayar
        return item
    elif hasattr(item, "__dict__"):
        bank_info = getattr(item, "bank_info", None)
        instructions = getattr(item, "instructions", None)
        info_dict = bank_info if isinstance(bank_info, dict) else {}
        name = getattr(item, "name", "")
        pm_type = getattr(item, "type", None)
        bank_name = (
            info_dict.get("bank_name")
            or info_dict.get("bank")
            or name
        )
        type_name = resolve_payment_type_name(pm_type)
        cara_bayar = resolve_cara_bayar(item, pm_type, name, bank_name, instructions=instructions)

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
