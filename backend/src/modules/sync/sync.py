import json
import re
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from taskiq import TaskiqDepends

from ...infrastructure.logging.receiver import get_receiver_logger
from ...infrastructure.taskiq.brokers import default_broker
from ...infrastructure.taskiq.deps import get_db_session
from ..customer.models import Customer
from ..product.models import ProductVariant
from ..store.models import (
    Store,
    StoreChannel,
    StoreChannelGroup,
    StoreGroup,
    StoreTier,
)

# Dedicated daily-rotating loggers per receiver endpoint
item_branch_logger = get_receiver_logger("item-branch", "item-branch")
base_price_logger = get_receiver_logger("base-price", "base-price")
customer_master_logger = get_receiver_logger("customer-master", "customer-master")

# Default tier used for stores created from JDE branch sync
DEFAULT_STORE_TIER_CODE = "DEFAULT"
DEFAULT_STORE_TIER_NAME = "Default"


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


def _extract_branches(payload: Any) -> list[dict[str, Any]]:
    """Collect every ``branches`` entry from a JDE item-branch payload.

    The payload is typically a list of ``{"short_item_no": ..., "branches": [...]}``
    items, possibly wrapped in ``rowset``/``data``/``POS_*``.
    """
    items: list[Any] = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("branches"), list):
            items = [payload]
        else:
            for key in ("rowset", "data"):
                if isinstance(payload.get(key), list):
                    items = payload[key]
                    break
            if not items:
                for value in payload.values():
                    if isinstance(value, dict):
                        inner = value.get("rowset") or value.get("data")
                        if isinstance(inner, list):
                            items = inner
                            break

    branches: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("branches"), list):
            branches.extend(item["branches"])
    return branches


async def _get_or_create(
    db: AsyncSession,
    model: Any,
    match: dict[str, Any],
    defaults: dict[str, Any],
) -> tuple[Any, bool]:
    """Get the first non-deleted row matching ``match`` or create it.

    Returns the instance and whether it was newly created.
    """
    conditions = [getattr(model, k) == v for k, v in match.items()]
    conditions.append(model.deleted == False)  # noqa: E712
    result = await db.execute(select(model).where(*conditions))
    obj = result.scalars().first()
    if obj is not None:
        for key, value in defaults.items():
            setattr(obj, key, value)
        return obj, False
    obj = model(**match, **defaults)
    db.add(obj)
    await db.flush()
    return obj, True


async def _get_or_create_default_tier(db: AsyncSession) -> StoreTier:
    """Return the default ``StoreTier`` (creating it if necessary)."""
    tier, _ = await _get_or_create(
        db,
        StoreTier,
        {"code": DEFAULT_STORE_TIER_CODE},
        {"name": DEFAULT_STORE_TIER_NAME},
    )
    return tier


async def sync_branch_stores_data(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """Build the store hierarchy (store_group, store, channel_group, channel)
    from the ``branches`` data of a JDE item-branch payload.

    Mapping (confirmed with domain owner):
        store_group        <- business_unit
        store              <- cabang_code (+ cabang_desc), under its business_unit
        store_channel_group <- stocking_type
        store_channel      <- program_id, under its store + channel_group

    Returns a summary of created/updated records.
    """
    logger = item_branch_logger
    branches = _extract_branches(payload)
    if not branches:
        logger.warning("Tidak ada data branch untuk disinkronisasi ke store.")
        return {"stores_created": 0, "stores_updated": 0}

    tier = await _get_or_create_default_tier(db)

    group_cache: dict[str, StoreGroup] = {}
    channel_group_cache: dict[str, StoreChannelGroup] = {}
    store_cache: dict[str, Store] = {}

    created = updated = 0

    for branch in branches:
        business_unit = str(branch.get("business_unit") or "").strip()
        cabang_code = str(branch.get("cabang_code") or "").strip()
        cabang_desc = str(branch.get("cabang_desc") or "").strip()
        stocking_type = str(branch.get("stocking_type") or "").strip()
        program_id = str(branch.get("program_id") or "").strip()

        if not business_unit or not cabang_code:
            logger.warning(f"Melewati branch karena business_unit/cabang_code kosong: {branch}")
            continue

        # store_group <- business_unit
        if business_unit not in group_cache:
            group, is_new = await _get_or_create(
                db,
                StoreGroup,
                {"code": business_unit},
                {"name": business_unit},
            )
            group_cache[business_unit] = group
            created += int(is_new)
            if not is_new:
                updated += 1
        group = group_cache[business_unit]

        # store <- cabang_code under its business_unit
        if cabang_code not in store_cache:
            store, is_new = await _get_or_create(
                db,
                Store,
                {"code": cabang_code},
                {
                    "name": cabang_desc or cabang_code,
                    "store_group_id": group.id,
                    "tier_id": tier.id,
                },
            )
            store_cache[cabang_code] = store
            created += int(is_new)
            if not is_new:
                updated += 1
        else:
            store = store_cache[cabang_code]

        # store_channel_group <- stocking_type
        if stocking_type and stocking_type not in channel_group_cache:
            channel_group, cg_is_new = await _get_or_create(
                db,
                StoreChannelGroup,
                {"code": stocking_type},
                {"name": stocking_type},
            )
            channel_group_cache[stocking_type] = channel_group
            created += int(cg_is_new)
            if not cg_is_new:
                updated += 1

        # store_channel <- program_id (unique per store, hence prefixed)
        if program_id:
            cg = channel_group_cache.get(stocking_type)
            if cg is None:
                cg, _ = await _get_or_create(
                    db,
                    StoreChannelGroup,
                    {"code": stocking_type or "DEFAULT"},
                    {"name": stocking_type or "Default"},
                )
                channel_group_cache[stocking_type or "DEFAULT"] = cg
            channel_code = f"{cabang_code}-{program_id}"
            _, ch_is_new = await _get_or_create(
                db,
                StoreChannel,
                {"code": channel_code, "store_id": store.id},
                {"name": program_id, "store_channel_group_id": cg.id},
            )
            created += int(ch_is_new)
            if not ch_is_new:
                updated += 1

    await db.commit()
    logger.info(f"Sinkronisasi store dari branch selesai: {created} dibuat, {updated} diperbarui.")
    return {"stores_created": created, "stores_updated": updated}


async def sync_base_price_data(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute synchronization of JDE base prices into database."""
    logger = base_price_logger
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
    logger = customer_master_logger
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
                        # Link to the externally managed ``users`` table (UUID PK) by email.
                        user_stmt = text(
                            "SELECT id FROM users "
                            "WHERE lower(trim(email)) = :email AND deleted = false "
                            "LIMIT 1"
                        )
                        user_res = await db.execute(user_stmt, {"email": email.lower()})
                        user_id = user_res.scalar_one_or_none()

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

                # NOTE: The ``addresses`` table in this database is user-scoped and
                # requires a ``city_id``; JDE customer-master rows have neither, so
                # the raw address text is preserved in ``customer.meta`` (jde_data)
                # instead of being written to ``addresses``.

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
    """Background task to sync item branch (store hierarchy) data."""
    logger = item_branch_logger
    try:
        return await sync_branch_stores_data(db, payload)
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
    logger = base_price_logger
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
    logger = customer_master_logger
    try:
        return await sync_customer_master_data(db, payload)
    except Exception as e:
        logger.error(f"Gagal dalam background task sinkronisasi Customer Master: {str(e)}", exc_info=True)
        await db.rollback()
        raise e
