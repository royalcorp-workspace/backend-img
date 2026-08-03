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


def normalize_rowset(payload: dict[str, Any], endpoint: str = "") -> list[dict[str, Any]]:
    """Normalize JDE payload rowset dynamically.

    Standard keys: ``rowset``, ``data``, ``POS_*`` wrappers.
    Endpoint keys: ``branches``, ``items``, ``stores``, ``rows`` for item-branch;
    ``customers`` for customer-master.
    For item-branch, if no known key is found, the first top-level list of dicts
    is returned as a fallback so unknown payload shapes still work.
    """
    if not isinstance(payload, dict):
        return []
    preferred_keys = ("rowset", "data")
    if endpoint == "item-branch":
        preferred_keys = (*preferred_keys, "branches", "items", "stores", "rows")
    elif endpoint == "customer-master":
        preferred_keys = (*preferred_keys, "customers", "branches")
    for key in preferred_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value or []

    pos_key = next((k for k in payload.keys() if k.startswith("POS_")), None)
    if not pos_key:
        pos_key = next((k for k, v in payload.items() if isinstance(v, dict) and ("rowset" in v or "data" in v)), None)

    if pos_key:
        v = payload[pos_key]
        if isinstance(v, dict):
            return v.get("rowset") or v.get("data") or []

    if endpoint == "item-branch":
        for key, value in payload.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
    return []


def _extract_branches(payload: Any) -> list[dict[str, Any]]:
    """Collect every ``branches`` / ``stores`` entry from a JDE item-branch payload.

    The payload is typically a list of ``{"short_item_no": ..., "branches": [...]}``
    items, or a flat list of branch/store objects, possibly wrapped in
    ``rowset``/``data``/``POS_*``.
    """
    items: list[Any] = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("branches"), list) or isinstance(payload.get("stores"), list):
            items = [payload]
        else:
            for key in ("rowset", "data", "branches", "stores"):
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
        if not isinstance(item, dict):
            continue
        branch_list = item.get("branches") or item.get("stores")
        if isinstance(branch_list, list):
            branches.extend(branch_list)
        elif item.get("business_unit") or item.get("cabang_code"):
            branches.append(item)
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
    rowset = normalize_rowset(payload, endpoint="base-price")
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

        prices = item.get("prices")
        if isinstance(prices, list) and prices:
            first_price = prices[0]
            price_val = (
                first_price.get("base_price")
                or first_price.get("price")
                or first_price.get("amount")
                or first_price.get("price_value")
                or first_price.get("oprc")
                or first_price.get("uprc")
                or first_price.get("bpup")
            )
            logger.info(
                f"Base Price: SKU '{sku}' prices[0]=base_price={first_price.get('base_price')} price_val={price_val}"
            )
        else:
            price_val = (
                item.get("price")
                or item.get("base_price")
                or item.get("amount")
                or item.get("price_value")
                or item.get("oprc")
                or item.get("uprc")
                or item.get("bpup")
            )
            logger.info(f"Base Price: SKU '{sku}' no-prices path, price_val={price_val}")

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
                    old_price = variant.price
                    variant.price = new_price

                    if variant.product:
                        variant.product.base_price = str(new_price)

                    await db.flush()
                    await db.refresh(variant)
                    results["updated_variants"] += 1
                    logger.info(
                        f"Base Price: Berhasil menyelaraskan SKU '{sku}' "
                        f"old_price={old_price} new_price={new_price} db_price_after={variant.price}"
                    )
                else:
                    results["not_found_variants"] += 1
                    logger.warning(f"Base Price: SKU '{sku}' tidak ditemukan di database")
        except Exception as e:
            logger.error(f"Gagal menyelaraskan Base Price SKU '{sku}': {str(e)}", exc_info=True)
            results["failed_items"] += 1

    await db.commit()
    logger.info(f"Sinkronisasi Base Price selesai: {results}")
    return results


async def sync_customer_master_data(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute synchronization of JDE Customer Master into store management.

    Maps JDE customer-master rows into store hierarchy:
        store_group        <- business_unit / bu
        store              <- customer code (an8) / branch code
        store_channel_group <- stocking_type / txct
        store_channel      <- program_id / unique per store

    Credit limit from JDE (crlmt / credit_limit) is written to store.credit_limit.
    """
    logger = customer_master_logger
    rowset = normalize_rowset(payload, endpoint="customer-master")
    total_items = len(rowset)
    logger.info(f"Memulai sinkronisasi Customer Master ke Store Management. Total data: {total_items}")

    results = {
        "total_items": total_items,
        "inserted_stores": 0,
        "updated_stores": 0,
        "failed_items": 0,
    }

    tier = await _get_or_create_default_tier(db)

    group_cache: dict[str, StoreGroup] = {}
    channel_group_cache: dict[str, StoreChannelGroup] = {}
    store_cache: dict[str, Store] = {}

    for item in rowset:
        store_code = str(item.get("business_unit") or item.get("bu") or "").strip()

        store_name = (
            item.get("name")
            or item.get("alph")
            or item.get("alpha_name")
            or item.get("fullname")
            or item.get("customer_name")
            or item.get("cabang_desc")
        )
        if store_name:
            store_name = str(store_name).strip()

        business_unit = str(item.get("business_unit") or item.get("bu") or "").strip()
        stocking_type = str(item.get("stocking_type") or item.get("txct") or "").strip()
        program_id = str(item.get("program_id") or "").strip()
        credit_limit = safe_float(
            item.get("credit_limit")
            or item.get("crlmt")
            or item.get("crlimit")
            or 0
        )
        phone = item.get("phone") or item.get("ph1") or item.get("phone_number")
        if phone:
            phone = str(phone).strip()
        else:
            phone = "-"
        email = item.get("email") or item.get("eaem") or item.get("email_address")
        if email:
            email = str(email).strip()
        else:
            email = "-"
        address = item.get("address") or item.get("add1") or item.get("addr1")
        if address:
            address = str(address).strip()

        if not store_code:
            logger.warning(f"Melewati Customer Master karena business_unit/store_code kosong: {item}")
            results["failed_items"] += 1
            continue

        try:
            async with db.begin_nested():
                if business_unit not in group_cache:
                    group, _ = await _get_or_create(
                        db,
                        StoreGroup,
                        {"code": business_unit},
                        {"name": business_unit},
                    )
                    group_cache[business_unit] = group
                group = group_cache[business_unit]

                if store_code not in store_cache:
                    store, is_new = await _get_or_create(
                        db,
                        Store,
                        {"code": store_code},
                        {
                            "name": store_name or store_code,
                            "store_group_id": group.id,
                            "tier_id": tier.id,
                            "credit_limit": credit_limit,
                            "phone": phone,
                            "email": email,
                            "address": address,
                            "status": True,
                        },
                    )
                    store_cache[store_code] = store
                    if is_new:
                        results["inserted_stores"] += 1
                    else:
                        results["updated_stores"] += 1
                else:
                    store = store_cache[store_code]
                    store.name = store_name or store.name
                    store.credit_limit = credit_limit
                    if phone:
                        store.phone = phone
                    if email:
                        store.email = email
                    if address:
                        store.address = address
                    results["updated_stores"] += 1

                if stocking_type and stocking_type not in channel_group_cache:
                    cg, _ = await _get_or_create(
                        db,
                        StoreChannelGroup,
                        {"code": stocking_type},
                        {"name": stocking_type},
                    )
                    channel_group_cache[stocking_type] = cg

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
                    channel_code = f"{store_code}-{program_id}"
                    _, ch_is_new = await _get_or_create(
                        db,
                        StoreChannel,
                        {"code": channel_code, "store_id": store.id},
                        {"name": program_id, "store_channel_group_id": cg.id},
                    )
                    if ch_is_new:
                        results["inserted_stores"] += 1
                    else:
                        results["updated_stores"] += 1

                await db.flush()
                logger.info(
                    f"Customer Master: Berhasil menyelaraskan store '{store_code}' ({store_name}) credit_limit={credit_limit}"
                )
        except Exception as e:
            logger.error(f"Gagal menyelaraskan Customer Master untuk '{store_code}': {str(e)}", exc_info=True)
            results["failed_items"] += 1

    await db.commit()
    logger.info(f"Sinkronisasi Customer Master ke Store Management selesai: {results}")
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
