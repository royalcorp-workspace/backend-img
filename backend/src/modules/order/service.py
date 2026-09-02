import datetime
import json
import random
import string
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...infrastructure.logging import get_logger
from ..add_to_cart.models import AddToCartItem
from ..common.exceptions import ResourceNotFoundError
from ..customer.models import Customer
from .crud import crud_orders
from .models import Order, OrderItem, OrderVoid, VoidOrder
from .schemas import OrderCreate

logger = get_logger()

# Order status constants
STATUS_DRAFT = 0
STATUS_PENDING_APPROVAL = 1
STATUS_CONFIRMED = 2
STATUS_PROCESSING = 3
STATUS_SHIPPED = 4
STATUS_DELIVERED = 5
STATUS_CANCELLED = 6
STATUS_RETURNED = 7

# Payment status constants
PAYMENT_UNPAID = 0
PAYMENT_PAID = 1
PAYMENT_FAILED = 2
PAYMENT_REFUNDED = 3
PAYMENT_PARTIAL = 4

ORDER_STATUS_MAP: dict[int, str] = {
    STATUS_DRAFT: "Draft",
    STATUS_PENDING_APPROVAL: "Menunggu Persetujuan",
    STATUS_CONFIRMED: "Dikonfirmasi",
    STATUS_PROCESSING: "Diproses",
    STATUS_SHIPPED: "Dikirim",
    STATUS_DELIVERED: "Selesai",
    STATUS_CANCELLED: "Dibatalkan",
    STATUS_RETURNED: "Dikembalikan",
}

PAYMENT_STATUS_MAP: dict[int, str] = {
    PAYMENT_UNPAID: "Belum Bayar",
    PAYMENT_PAID: "Sudah Bayar",
    PAYMENT_FAILED: "Gagal",
    PAYMENT_REFUNDED: "Dikembalikan",
    PAYMENT_PARTIAL: "Dibayar Sebagian",
}


def _safe_uuid(val: Any) -> UUID | None:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception:
        return None


def _safe_float(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except Exception:
        return 0.0


def _safe_datetime(val: Any) -> Any:
    if val is None:
        return datetime.datetime.now()
    if isinstance(val, datetime.datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return val
    return val


def _resolve_status_label(status: int | None, is_void: bool = False, void_status: str | None = None) -> str:
    if is_void:
        return void_status or "Gagal Transaksi"
    if status is None:
        return "Unknown"
    return ORDER_STATUS_MAP.get(status, f"Status {status}")


def _resolve_payment_status_label(payment_status: int | None, is_void: bool = False) -> str:
    if is_void:
        return "Gagal Transaksi"
    if payment_status is None:
        return "Belum Dibayar"
    return PAYMENT_STATUS_MAP.get(payment_status, f"Payment Status {payment_status}")


def _order_to_dict(order: Order, void_data: dict[str, Any] | None = None) -> dict[str, Any]:
    is_void = bool(void_data) or (order.status in (5, 6, 7)) or (order.payment_status in (3, 5))

    status_label = _resolve_status_label(
        order.status,
        is_void=is_void,
        void_status=void_data.get("status") if void_data else None,
    )
    payment_status_label = _resolve_payment_status_label(order.payment_status, is_void=is_void)

    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_id": order.customer_id,
        "status": order.status,
        "status_label": status_label,
        "status_text": status_label,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "payment_status_label": payment_status_label,
        "payment_status_text": payment_status_label,
        "is_void": is_void,
        "void_reason": void_data.get("reason") if void_data else None,
        "voided_at": void_data.get("created_at") if void_data else None,
        "subtotal": _safe_float(order.subtotal),
        "tax": _safe_float(order.tax),
        "discount": _safe_float(order.discount),
        "total": _safe_float(order.total),
        "shipping_cost": _safe_float(getattr(order, "shipping_cost", 0.0)),
        "voucher_nominal": _safe_float(getattr(order, "voucher_nominal", 0.0)),
        "notes": order.notes,
        "meta": order.meta,
        "creator": order.creator,
        "editor": order.editor,
        "deleted": order.deleted,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "customer": (
            {
                "id": order.customer.id,
                "name": order.customer.name,
                "email": order.customer.email,
                "phone": order.customer.phone,
                "user_id": order.customer.user_id,
                "created_at": order.customer.created_at,
                "updated_at": order.customer.updated_at,
                "deleted": order.customer.deleted,
            }
            if order.customer
            else None
        ),
        "items": [
            {
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "product_variant_id": item.product_variant_id,
                "quantity": item.quantity,
                "unit_price": _safe_float(item.unit_price),
                "discount_nominal": _safe_float(item.discount_nominal),
                "discount_percent": _safe_float(item.discount_percent),
                "total": _safe_float(item.total),
                "name": item.name,
                "item_notes": item.item_notes,
                "meta": item.meta,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "product": (
                    {
                        "id": item.product.id,
                        "name": item.product.name,
                        "slug": item.product.slug,
                    }
                    if item.product
                    else None
                ),
                "variant": (
                    {
                        "id": item.variant.id,
                        "product_id": item.variant.product_id,
                        "variant_name": item.variant.variant_name,
                        "sell_price": _safe_float(item.variant.sell_price),
                        "sku": item.variant.sku,
                    }
                    if item.variant
                    else None
                ),
            }
            for item in (order.items or [])
        ],
    }


def _void_order_to_dict(void_order: VoidOrder) -> dict[str, Any]:
    """Convert a VoidOrder row (from void_orders table) to an OrderRead dictionary."""
    order_data = void_order.order_data if isinstance(void_order.order_data, dict) else {}
    items_data = void_order.order_items_data if isinstance(void_order.order_items_data, list) else []

    order_id = void_order.id
    customer_id = void_order.customer_id or _safe_uuid(order_data.get("customer_id"))
    order_number = void_order.order_number or order_data.get("order_number")

    formatted_items = []
    for item in items_data:
        if not isinstance(item, dict):
            continue
        product_info = item.get("product") if isinstance(item.get("product"), dict) else None
        variant_info = item.get("variant") if isinstance(item.get("variant"), dict) else None

        item_id = _safe_uuid(item.get("id"))
        product_id = _safe_uuid(item.get("product_id"))
        variant_id = _safe_uuid(item.get("product_variant_id"))

        formatted_items.append({
            "id": item_id,
            "order_id": order_id,
            "product_id": product_id,
            "product_variant_id": variant_id,
            "quantity": int(item.get("quantity") or 1),
            "unit_price": _safe_float(item.get("unit_price")),
            "discount_nominal": _safe_float(item.get("discount_nominal")),
            "discount_percent": _safe_float(item.get("discount_percent")),
            "total": _safe_float(item.get("total")),
            "name": item.get("name") or (product_info.get("name") if product_info else None),
            "item_notes": item.get("item_notes"),
            "meta": item.get("meta") if isinstance(item.get("meta"), dict) else None,
            "created_at": _safe_datetime(item.get("created_at") or void_order.created_at),
            "updated_at": _safe_datetime(item.get("updated_at") or void_order.updated_at or void_order.created_at),
            "product": product_info,
            "variant": variant_info,
        })

    created_at = _safe_datetime(order_data.get("created_at") or void_order.created_at)
    updated_at = _safe_datetime(void_order.voided_at or void_order.updated_at or void_order.created_at)

    return {
        "id": order_id,
        "order_number": order_number,
        "customer_id": customer_id,
        "status": 5,
        "status_label": "Gagal Transaksi",
        "status_text": "Gagal Transaksi",
        "payment_method": order_data.get("payment_method"),
        "payment_status": 3,
        "payment_status_label": "Gagal Transaksi",
        "payment_status_text": "Gagal Transaksi",
        "is_void": True,
        "void_reason": void_order.void_reason or "Batas waktu pembayaran telah habis (Auto Void)",
        "voided_at": void_order.voided_at or void_order.created_at,
        "subtotal": _safe_float(order_data.get("subtotal")),
        "tax": _safe_float(order_data.get("tax")),
        "discount": _safe_float(order_data.get("discount")),
        "total": _safe_float(order_data.get("total")),
        "shipping_cost": _safe_float(order_data.get("shipping_cost")),
        "voucher_nominal": _safe_float(order_data.get("voucher_nominal")),
        "notes": order_data.get("notes"),
        "meta": order_data.get("meta") if isinstance(order_data.get("meta"), dict) else {"source": "void_orders"},
        "created_at": created_at,
        "updated_at": updated_at,
        "customer": order_data.get("customer") if isinstance(order_data.get("customer"), dict) else None,
        "items": formatted_items,
    }


async def _fetch_voids_map_for_orders(db: AsyncSession, order_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
    """Fetch void details map for a list of order IDs from void_orders or voids table."""
    if not order_ids:
        return {}
    voids_map: dict[UUID, dict[str, Any]] = {}

    # 1. Try querying VoidOrder model (table void_orders)
    try:
        stmt = select(VoidOrder).where(VoidOrder.id.in_(order_ids))
        res = await db.execute(stmt)
        for row in res.scalars().all():
            voids_map[row.id] = {
                "id": row.id,
                "order_id": row.id,
                "customer_id": row.customer_id,
                "reason": row.void_reason or "Batas waktu pembayaran telah habis",
                "status": "gagal transaksi",
                "meta": row.order_data.get("meta") if isinstance(row.order_data, dict) else None,
                "created_at": row.voided_at or row.created_at,
                "updated_at": row.updated_at or row.created_at,
            }
    except Exception:
        pass

    # 2. Try raw fallback on voids table if not found
    missing_ids = [oid for oid in order_ids if oid not in voids_map]
    if missing_ids:
        try:
            raw_stmt = text(
                "SELECT id, order_id, customer_id, reason, status, created_at, updated_at FROM voids WHERE order_id = ANY(:oids)"
            )
            raw_res = await db.execute(raw_stmt, {"oids": missing_ids})
            for r in raw_res.fetchall():
                oid = r[1]
                voids_map[oid] = {
                    "id": r[0],
                    "order_id": r[1],
                    "customer_id": r[2],
                    "reason": r[3],
                    "status": r[4] or "gagal transaksi",
                    "created_at": r[5],
                    "updated_at": r[6],
                }
        except Exception:
            pass

    return voids_map


class OrderService:
    async def get_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        customer_id: UUID | None = None,
        status: int | None = None,
        payment_status: int | None = None,
        **filters,
    ) -> dict[str, Any]:
        query = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
            )
            .where(or_(Order.deleted.is_(False), Order.deleted.is_(None)))
        )
        count_query = select(func.count()).select_from(Order).where(or_(Order.deleted.is_(False), Order.deleted.is_(None)))

        if customer_id is not None:
            # Resolve customer_ids including user_id
            cust_stmt = select(Customer.id).where(or_(Customer.id == customer_id, Customer.user_id == customer_id))
            cust_res = await db.execute(cust_stmt)
            matched_cids = [r for r in cust_res.scalars().all()]
            if customer_id not in matched_cids:
                matched_cids.append(customer_id)

            query = query.where(Order.customer_id.in_(matched_cids))
            count_query = count_query.where(Order.customer_id.in_(matched_cids))

        if status is not None:
            query = query.where(Order.status == status)
            count_query = count_query.where(Order.status == status)

        if payment_status is not None:
            query = query.where(Order.payment_status == payment_status)
            count_query = count_query.where(Order.payment_status == payment_status)

        for key, value in filters.items():
            if hasattr(Order, key) and value is not None:
                query = query.where(getattr(Order, key) == value)
                count_query = count_query.where(getattr(Order, key) == value)

        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        orders = result.scalars().all()
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch void data map
        order_ids = [o.id for o in orders]
        voids_map = await _fetch_voids_map_for_orders(db, order_ids)

        return {
            "data": [_order_to_dict(o, voids_map.get(o.id)) for o in orders],
            "total_count": total,
            "has_more": (skip + len(orders)) < total,
        }

    async def get_customer_history(
        self,
        db: AsyncSession,
        customer_id: UUID,
        skip: int = 0,
        limit: int = 10,
        status: int | None = None,
    ) -> dict[str, Any]:
        """
        Get complete order history specifically for a customer_id,
        combining active orders and void_orders (with status gagal transaksi).
        """
        # Resolve customer IDs (matching by Customer.id or Customer.user_id)
        cust_stmt = select(Customer.id).where(or_(Customer.id == customer_id, Customer.user_id == customer_id))
        cust_res = await db.execute(cust_stmt)
        matched_cids = [r for r in cust_res.scalars().all()]
        if customer_id not in matched_cids:
            matched_cids.append(customer_id)

        # 1. Fetch from orders table
        orders_query = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
            )
            .where(
                Order.customer_id.in_(matched_cids),
                or_(Order.deleted.is_(False), Order.deleted.is_(None)),
            )
        )
        if status is not None:
            orders_query = orders_query.where(Order.status == status)

        orders_res = await db.execute(orders_query)
        active_orders = orders_res.scalars().all()
        active_order_ids = [o.id for o in active_orders]

        # Fetch voids map for active orders
        voids_map = await _fetch_voids_map_for_orders(db, active_order_ids)
        formatted_orders = [_order_to_dict(o, voids_map.get(o.id)) for o in active_orders]

        # 2. Fetch from void_orders table
        formatted_voids = []
        if status is None or status in (5, 6, 7):
            try:
                void_query = select(VoidOrder).where(VoidOrder.customer_id.in_(matched_cids))
                void_res = await db.execute(void_query)
                void_records = void_res.scalars().all()
                for vr in void_records:
                    if vr.id not in active_order_ids:
                        formatted_voids.append(_void_order_to_dict(vr))
            except Exception as e:
                logger.warning(f"ORM void_orders query failed: {e}, attempting raw fallback")
                try:
                    str_cids = [str(cid) for cid in matched_cids]
                    raw_sql = text("""
                        SELECT id, order_number, customer_id, order_data, order_items_data, void_reason, voided_at, created_at, updated_at
                        FROM void_orders
                        WHERE customer_id = ANY(:cids) OR (order_data->>'customer_id' = ANY(:str_cids))
                    """)
                    raw_res = await db.execute(raw_sql, {"cids": matched_cids, "str_cids": str_cids})
                    for r in raw_res.fetchall():
                        if r[0] not in active_order_ids:
                            vo = VoidOrder(
                                id=r[0],
                                order_number=r[1],
                                customer_id=r[2],
                                order_data=r[3] if isinstance(r[3], dict) else (json.loads(r[3]) if isinstance(r[3], str) else {}),
                                order_items_data=r[4] if isinstance(r[4], (list, dict)) else (json.loads(r[4]) if isinstance(r[4], str) else []),
                                void_reason=r[5],
                                voided_at=r[6],
                            )
                            vo.created_at = r[7]
                            vo.updated_at = r[8]
                            formatted_voids.append(_void_order_to_dict(vo))
                except Exception:
                    pass

        # 3. Combine and sort by created_at descending
        all_orders = formatted_orders + formatted_voids

        def _get_sort_key(item: dict[str, Any]):
            ca = item.get("created_at")
            if isinstance(ca, datetime.datetime):
                return ca.timestamp()
            elif isinstance(ca, str):
                try:
                    return datetime.datetime.fromisoformat(ca.replace("Z", "+00:00")).timestamp()
                except Exception:
                    pass
            return 0.0

        all_orders.sort(key=_get_sort_key, reverse=True)

        total_count = len(all_orders)
        paginated_items = all_orders[skip : skip + limit]

        return {
            "data": paginated_items,
            "total_count": total_count,
            "has_more": (skip + len(paginated_items)) < total_count,
        }

    async def get_void_orders_by_customer(
        self,
        db: AsyncSession,
        customer_id: UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Get only void / failed transactions for a specific customer_id."""
        # Resolve customer IDs (matching by Customer.id or Customer.user_id)
        cust_stmt = select(Customer.id).where(or_(Customer.id == customer_id, Customer.user_id == customer_id))
        cust_res = await db.execute(cust_stmt)
        matched_cids = [r for r in cust_res.scalars().all()]
        if customer_id not in matched_cids:
            matched_cids.append(customer_id)

        # 1. Try ORM query
        try:
            void_query = (
                select(VoidOrder)
                .where(VoidOrder.customer_id.in_(matched_cids))
                .order_by(VoidOrder.created_at.desc())
            )
            count_query = (
                select(func.count())
                .select_from(VoidOrder)
                .where(VoidOrder.customer_id.in_(matched_cids))
            )

            total_res = await db.execute(count_query)
            total = total_res.scalar() or 0

            res = await db.execute(void_query.offset(skip).limit(limit))
            void_records = res.scalars().all()

            if void_records or total > 0:
                return {
                    "data": [_void_order_to_dict(vr) for vr in void_records],
                    "total_count": total,
                    "has_more": (skip + len(void_records)) < total,
                }
        except Exception as e:
            logger.warning(f"ORM get_void_orders_by_customer failed: {e}, trying raw SQL")

        # 2. Raw SQL fallback
        try:
            str_cids = [str(cid) for cid in matched_cids]
            raw_count = text("""
                SELECT COUNT(*) FROM void_orders
                WHERE customer_id = ANY(:cids) OR (order_data->>'customer_id' = ANY(:str_cids))
            """)
            raw_sql = text("""
                SELECT id, order_number, customer_id, order_data, order_items_data, void_reason, voided_at, created_at, updated_at
                FROM void_orders
                WHERE customer_id = ANY(:cids) OR (order_data->>'customer_id' = ANY(:str_cids))
                ORDER BY created_at DESC
                OFFSET :skip LIMIT :limit
            """)

            count_res = await db.execute(raw_count, {"cids": matched_cids, "str_cids": str_cids})
            total = count_res.scalar() or 0

            rows_res = await db.execute(raw_sql, {"cids": matched_cids, "str_cids": str_cids, "skip": skip, "limit": limit})
            rows = rows_res.fetchall()

            data = []
            for r in rows:
                vo = VoidOrder(
                    id=r[0],
                    order_number=r[1],
                    customer_id=r[2],
                    order_data=r[3] if isinstance(r[3], dict) else (json.loads(r[3]) if isinstance(r[3], str) else {}),
                    order_items_data=r[4] if isinstance(r[4], (list, dict)) else (json.loads(r[4]) if isinstance(r[4], str) else []),
                    void_reason=r[5],
                    voided_at=r[6],
                )
                vo.created_at = r[7]
                vo.updated_at = r[8]
                data.append(_void_order_to_dict(vo))

            return {
                "data": data,
                "total_count": total,
                "has_more": (skip + len(data)) < total,
            }
        except Exception as e:
            logger.error(f"Raw get_void_orders_by_customer failed: {e}")

        return {
            "data": [],
            "total_count": 0,
            "has_more": False,
        }

    async def get_by_id(self, db: AsyncSession, order_id: UUID) -> dict[str, Any]:
        query = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
            )
            .where(Order.id == order_id, or_(Order.deleted.is_(False), Order.deleted.is_(None)))
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        if order:
            voids_map = await _fetch_voids_map_for_orders(db, [order.id])
            return _order_to_dict(order, voids_map.get(order.id))

        # Check in void_orders table
        try:
            void_res = await db.execute(
                select(VoidOrder).where(VoidOrder.id == order_id)
            )
            void_order = void_res.scalar_one_or_none()
            if void_order:
                return _void_order_to_dict(void_order)
        except Exception:
            pass

        raise ResourceNotFoundError(f"Order with ID {order_id} not found")

    async def create(self, db: AsyncSession, order_in: OrderCreate) -> Any:
        order_data = order_in.model_dump(
            exclude={"items", "cart_item_ids", "shipping_address_id", "courier_id", "shipping_cost", "voucher_id"}
        )

        # Generate Order Number
        now = datetime.datetime.now()
        random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        order_number = f"ORD-{now.strftime('%y%m%d')}-{random_str}"
        order_data["order_number"] = order_number

        # Map mobile fields to db fields
        if order_in.courier_id:
            order_data["courier_id"] = order_in.courier_id
        if order_in.shipping_cost:
            order_data["shipping_cost"] = order_in.shipping_cost
        if order_in.voucher_id:
            order_data["voucher_id"] = order_in.voucher_id
        if order_in.shipping_address_id:
            order_data["shipping_addresses_id"] = order_in.shipping_address_id

        # Inject platform info into meta
        meta = order_data.get("meta") or {}
        meta["platform"] = "mobile_app"
        order_data["meta"] = meta

        order = Order(**order_data)
        db.add(order)
        await db.flush()

        # Handle Cart Flow
        if order_in.cart_item_ids:
            for cart_item_id in order_in.cart_item_ids:
                cart_item = await db.scalar(select(AddToCartItem).where(AddToCartItem.id == cart_item_id))
                if cart_item:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=cart_item.product_id,
                        product_variant_id=cart_item.product_variant_id,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.unit_price,
                        discount_nominal=cart_item.discount_nominal,
                        discount_percent=cart_item.discount_percent,
                        total=cart_item.total,
                        name=cart_item.name,
                        item_notes=cart_item.item_notes,
                        meta=cart_item.meta,
                    )
                    db.add(order_item)
                    await db.delete(cart_item)
        # Handle Direct Purchase Flow
        elif order_in.items:
            for item_in in order_in.items:
                item_data = item_in.model_dump(exclude_unset=True)
                order_item = OrderItem(order_id=order.id, **item_data)
                db.add(order_item)

        await db.commit()
        return await self.get_by_id(db, order.id)

    async def delete(self, db: AsyncSession, order_id: UUID) -> None:
        order = await crud_orders.get(db=db, id=order_id, deleted=False)
        if not order:
            raise ResourceNotFoundError(f"Order with ID {order_id} not found")
        await crud_orders.delete(db=db, id=order_id)

