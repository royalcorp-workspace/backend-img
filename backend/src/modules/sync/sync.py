import json
import logging
import logging.handlers
import re
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from taskiq import TaskiqDepends

from ...infrastructure.taskiq.brokers import default_broker
from ...infrastructure.taskiq.deps import get_db_session
from ..customer.models import Address, Customer
from ..product.models import ProductVariant
from ..user.models import User

# Setup dedicated file logger for POS sync
BACKEND_DIR = Path(__file__).resolve().parents[3]
LOGS_DIR = BACKEND_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
SYNC_LOG_FILE = LOGS_DIR / "pos_sync.log"

sync_file_handler = logging.handlers.TimedRotatingFileHandler(
    SYNC_LOG_FILE, when="midnight", interval=1, backupCount=30, encoding="utf-8"
)
sync_file_handler.suffix = "%Y-%m-%d"
sync_file_handler.extMatch = r"^\d{4}-\d{2}-\d{2}(\.\w+)?$"
sync_file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s")
sync_file_handler.setFormatter(sync_file_formatter)
sync_file_handler.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(sync_file_handler)


def safe_int(val: Any) -> int:
    """Safely convert value to int."""
    if not val or str(val).strip() == "":
        return 0
    try:
        cleaned = re.sub(r"[^\d-]", "", str(val).strip())
        return int(cleaned)
    except ValueError:
        return 0


def safe_float(val: Any) -> float:
    """Safely convert value to float."""
    if not val or str(val).strip() == "":
        return 0.0
    try:
        cleaned = re.sub(r"[^\d.,-]", "", str(val).strip())
        return float(cleaned.replace(",", ""))
    except ValueError:
        return 0.0


def normalize_rowset(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize JDE payload rowset dynamically."""
    if not isinstance(payload, dict):
        return []
    if "rowset" in payload:
        return payload["rowset"] or []
    if "data" in payload:
        return payload["data"] or []
    
    # Try to find a key that starts with "POS_" or has "rowset"/"data"
    pos_key = next((k for k in payload.keys() if k.startswith("POS_")), None)
    if not pos_key:
        pos_key = next((k for k, v in payload.items() if isinstance(v, dict) and ("rowset" in v or "data" in v)), None)

    if pos_key:
        v = payload[pos_key]
        if isinstance(v, dict):
            return v.get("rowset") or v.get("data") or []
    return []


async def sync_item_branch_data(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute synchronization of JDE item-branch (inventory stocks) into database."""
    rowset = normalize_rowset(payload)
    total_items = len(rowset)
    logger.info(f"Memulai sinkronisasi Item Branch. Total data: {total_items}")

    results = {
        "total_items": total_items,
        "updated_variants": 0,
        "not_found_variants": 0,
        "failed_items": 0,
    }

    for item in rowset:
        sku = (
            item.get("sku") or 
            item.get("item") or 
            item.get("second_item_number") or 
            item.get("litm") or 
            item.get("itm") or 
            item.get("item_number") or 
            item.get("item_code")
        )
        if sku:
            sku = str(sku).strip()
        
        qty_val = (
            item.get("stock_qty") or 
            item.get("qty") or 
            item.get("quantity") or 
            item.get("quantity_on_hand") or 
            item.get("qty_on_hand") or 
            item.get("hand_qty") or 
            item.get("stock") or 
            item.get("pqoh") or 
            item.get("lipqoh")
        )
        
        branch = item.get("branch") or item.get("mcu") or item.get("branch_plant")
        if branch:
            branch = str(branch).strip()

        if not sku:
            logger.warning(f"Melewati baris Item Branch karena SKU/Item kosong: {item}")
            results["failed_items"] += 1
            continue

        try:
            async with db.begin_nested():
                stmt = select(ProductVariant).where(
                    func.lower(func.trim(ProductVariant.sku)) == sku.lower(),
                    ProductVariant.deleted == False  # noqa: E712
                )
                res = await db.execute(stmt)
                variant = res.scalar_one_or_none()

                if variant:
                    new_qty = safe_int(qty_val)
                    variant.stock_qty = new_qty
                    
                    if branch:
                        if variant.attributes is None:
                            variant.attributes = {}
                        variant.attributes["branch"] = branch
                    
                    results["updated_variants"] += 1
                    logger.info(f"Item Branch: Berhasil menyelaraskan SKU '{sku}' (Qty: {new_qty})")
                else:
                    results["not_found_variants"] += 1
                    logger.warning(f"Item Branch: SKU '{sku}' tidak ditemukan di database")
                
                await db.flush()
        except Exception as e:
            logger.error(f"Gagal menyelaraskan Item Branch SKU '{sku}': {str(e)}", exc_info=True)
            results["failed_items"] += 1

    await db.commit()
    logger.info(f"Sinkronisasi Item Branch selesai: {results}")
    return results


async def sync_base_price_data(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute synchronization of JDE base prices into database."""
    rowset = normalize_rowset(payload)
    total_items = len(rowset)
    logger.info(f"Memulai sinkronisasi Base Price. Total data: {total_items}")

    results = {
        "total_items": total_items,
        "updated_variants": 0,
        "not_found_variants": 0,
        "failed_items": 0,
    }

    for item in rowset:
        sku = (
            item.get("sku") or 
            item.get("item") or 
            item.get("second_item_number") or 
            item.get("litm") or 
            item.get("itm") or 
            item.get("item_number") or 
            item.get("item_code")
        )
        if sku:
            sku = str(sku).strip()

        price_val = (
            item.get("price") or 
            item.get("base_price") or 
            item.get("amount") or 
            item.get("price_value") or 
            item.get("oprc") or 
            item.get("uprc") or 
            item.get("bpup")
        )

        if not sku:
            logger.warning(f"Melewati baris Base Price karena SKU/Item kosong: {item}")
            results["failed_items"] += 1
            continue

        try:
            async with db.begin_nested():
                stmt = (
                    select(ProductVariant)
                    .options(selectinload(ProductVariant.product))
                    .where(
                        func.lower(func.trim(ProductVariant.sku)) == sku.lower(),
                        ProductVariant.deleted == False  # noqa: E712
                    )
                )
                res = await db.execute(stmt)
                variant = res.scalar_one_or_none()

                if variant:
                    new_price = safe_float(price_val)
                    variant.price = new_price
                    
                    if variant.product:
                        variant.product.base_price = str(new_price)

                    results["updated_variants"] += 1
                    logger.info(f"Base Price: Berhasil menyelaraskan SKU '{sku}' (Price: {new_price})")
                else:
                    results["not_found_variants"] += 1
                    logger.warning(f"Base Price: SKU '{sku}' tidak ditemukan di database")

                await db.flush()
        except Exception as e:
            logger.error(f"Gagal menyelaraskan Base Price SKU '{sku}': {str(e)}", exc_info=True)
            results["failed_items"] += 1

    await db.commit()
    logger.info(f"Sinkronisasi Base Price selesai: {results}")
    return results


async def sync_customer_master_data(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute synchronization of JDE Customer Master into database."""
    rowset = normalize_rowset(payload)
    total_items = len(rowset)
    logger.info(f"Memulai sinkronisasi Customer Master. Total data: {total_items}")

    results = {
        "total_items": total_items,
        "inserted_customers": 0,
        "updated_customers": 0,
        "inserted_addresses": 0,
        "updated_addresses": 0,
        "failed_items": 0,
    }

    for item in rowset:
        an8 = item.get("an8") or item.get("customer_id") or item.get("customer_code") or item.get("id")
        if an8:
            an8 = str(an8).strip()
            
        name = (
            item.get("name") or 
            item.get("alph") or 
            item.get("alpha_name") or 
            item.get("fullname") or 
            item.get("customer_name")
        )
        if name:
            name = str(name).strip()
            
        email = item.get("email") or item.get("eaem") or item.get("email_address")
        if email:
            email = str(email).strip()
            
        phone = item.get("phone") or item.get("ph1") or item.get("phone_number") or item.get("tele")
        if phone:
            phone = str(phone).strip()

        add1 = item.get("add1") or ""
        add2 = item.get("add2") or ""
        add3 = item.get("add3") or ""
        address_text = ", ".join(filter(None, [str(add1).strip(), str(add2).strip(), str(add3).strip()])) or item.get("address")
        if address_text:
            address_text = str(address_text).strip()
            
        postal_code = item.get("postal_code") or item.get("addz") or item.get("zip") or item.get("zipcode")
        if postal_code:
            postal_code = str(postal_code).strip()

        if not email and not phone:
            logger.warning(f"Melewati baris Customer Master karena Email dan Phone kosong: {item}")
            results["failed_items"] += 1
            continue
            
        if not name:
            name = email.split("@")[0] if email else f"JDE Customer {an8 or ''}"

        try:
            async with db.begin_nested():
                customer = None
                if email:
                    stmt = select(Customer).where(
                        func.lower(func.trim(Customer.email)) == email.lower(),
                        Customer.deleted == False  # noqa: E712
                    )
                    res = await db.execute(stmt)
                    customer = res.scalar_one_or_none()
                
                if not customer and phone:
                    stmt = select(Customer).where(
                        func.trim(Customer.phone) == phone,
                        Customer.deleted == False  # noqa: E712
                    )
                    res = await db.execute(stmt)
                    customer = res.scalar_one_or_none()

                meta_dict = {}
                if an8:
                    meta_dict["an8"] = an8
                meta_dict["synced_from"] = "JDE"
                meta_dict["jde_data"] = {k: v for k, v in item.items() if k not in ["password"]}

                if customer:
                    customer.name = name
                    if email:
                        customer.email = email
                    if phone:
                        customer.phone = phone
                    
                    existing_meta = {}
                    if customer.meta:
                        try:
                            existing_meta = json.loads(customer.meta)
                        except Exception:
                            existing_meta = {"raw": customer.meta}
                    existing_meta.update(meta_dict)
                    customer.meta = json.dumps(existing_meta)
                    
                    results["updated_customers"] += 1
                    logger.info(f"Customer Master: Berhasil memperbarui customer '{name}' ({email or phone})")
                else:
                    user_id = None
                    if email:
                        user_stmt = select(User).where(
                            func.lower(func.trim(User.email)) == email.lower(),
                            User.deleted == False  # noqa: E712
                        )
                        user_res = await db.execute(user_stmt)
                        user_obj = user_res.scalar_one_or_none()
                        if user_obj:
                            user_id = user_obj.id

                    customer = Customer(
                        name=name,
                        email=email or f"{an8 or phone or 'unknown'}@jde-sync.local",
                        phone=phone,
                        user_id=user_id,
                        meta=json.dumps(meta_dict),
                    )
                    db.add(customer)
                    await db.flush()
                    results["inserted_customers"] += 1
                    logger.info(f"Customer Master: Berhasil membuat customer baru '{name}' ({customer.email})")

                if address_text:
                    addr_stmt = select(Address).where(
                        Address.customer_id == customer.id,
                        func.lower(func.trim(Address.address)) == address_text.lower(),
                        Address.deleted == False  # noqa: E712
                    )
                    addr_res = await db.execute(addr_stmt)
                    address_obj = addr_res.scalar_one_or_none()

                    if address_obj:
                        address_obj.recipient_name = name
                        address_obj.phone = phone or customer.phone or "0"
                        address_obj.postal_code = postal_code
                        results["updated_addresses"] += 1
                    else:
                        cnt_stmt = select(func.count(Address.id)).where(
                            Address.customer_id == customer.id,
                            Address.deleted == False  # noqa: E712
                        )
                        cnt_res = await db.execute(cnt_stmt)
                        has_addresses = cnt_res.scalar() > 0

                        new_addr = Address(
                            customer_id=customer.id,
                            recipient_name=name,
                            phone=phone or customer.phone or "0",
                            address=address_text,
                            label="Alamat JDE",
                            postal_code=postal_code,
                            is_primary=not has_addresses,
                            creator="JDE Sync"
                        )
                        db.add(new_addr)
                        results["inserted_addresses"] += 1

                await db.flush()
        except Exception as e:
            logger.error(f"Gagal menyelaraskan Customer Master untuk '{name}': {str(e)}", exc_info=True)
            results["failed_items"] += 1

    await db.commit()
    logger.info(f"Sinkronisasi Customer Master selesai: {results}")
    return results


# Taskiq Background Tasks
@default_broker.task
async def sync_item_branch_task(
    payload: dict[str, Any],
    db: AsyncSession = TaskiqDepends(get_db_session),
) -> dict[str, Any]:
    """Background task to sync item branch data."""
    try:
        return await sync_item_branch_data(db, payload)
    except Exception as e:
        logger.error(f"Gagal dalam background task sinkronisasi Item Branch: {str(e)}", exc_info=True)
        await db.rollback()
        raise e


@default_broker.task
async def sync_base_price_task(
    payload: dict[str, Any],
    db: AsyncSession = TaskiqDepends(get_db_session),
) -> dict[str, Any]:
    """Background task to sync base price data."""
    try:
        return await sync_base_price_data(db, payload)
    except Exception as e:
        logger.error(f"Gagal dalam background task sinkronisasi Base Price: {str(e)}", exc_info=True)
        await db.rollback()
        raise e


@default_broker.task
async def sync_customer_master_task(
    payload: dict[str, Any],
    db: AsyncSession = TaskiqDepends(get_db_session),
) -> dict[str, Any]:
    """Background task to sync customer master data."""
    try:
        return await sync_customer_master_data(db, payload)
    except Exception as e:
        logger.error(f"Gagal dalam background task sinkronisasi Customer Master: {str(e)}", exc_info=True)
        await db.rollback()
        raise e
