"""Seed RBAC: roles, permissions, dan role-permission mapping.

Membuat 2 role:
  - admin  : semua permission (create/read/update/delete)
  - customer: hanya permission yang dibutuhkan customer (read + operasi sendiri)

Juga auto-assign role 'customer' ke semua user non-superuser yang belum punya role.

Usage:
    docker exec backend-img-api-1 python -m scripts.seed_rbac
    # atau dari root project:
    python -m backend.scripts.seed_rbac
"""

import asyncio
import sys
import os

# Pastikan src bisa di-import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from src.infrastructure.database.session import async_session

# =============================================================================
# DATA DEFINITION
# =============================================================================

ALL_PERMISSIONS = [
    # (name, action, subject, description)
    ("products:read",           "read",   "products",        "Lihat daftar & detail produk"),
    ("products:create",         "create", "products",        "Tambah produk baru"),
    ("products:update",         "update", "products",        "Edit produk"),
    ("products:delete",         "delete", "products",        "Hapus produk"),
    ("categories:read",         "read",   "categories",      "Lihat kategori"),
    ("categories:create",       "create", "categories",      "Tambah kategori"),
    ("categories:update",       "update", "categories",      "Edit kategori"),
    ("categories:delete",       "delete", "categories",      "Hapus kategori"),
    ("orders:read",             "read",   "orders",          "Lihat pesanan"),
    ("orders:create",           "create", "orders",          "Buat pesanan"),
    ("orders:update",           "update", "orders",          "Update pesanan"),
    ("orders:delete",           "delete", "orders",          "Hapus pesanan"),
    ("add_to_cart:read",        "read",   "add_to_cart",     "Lihat keranjang"),
    ("add_to_cart:create",      "create", "add_to_cart",     "Tambah ke keranjang"),
    ("add_to_cart:update",      "update", "add_to_cart",     "Update keranjang"),
    ("add_to_cart:delete",      "delete", "add_to_cart",     "Hapus dari keranjang"),
    ("customers:read",          "read",   "customers",       "Lihat data customer"),
    ("customers:create",        "create", "customers",       "Tambah customer"),
    ("customers:update",        "update", "customers",       "Edit customer"),
    ("customers:delete",        "delete", "customers",       "Hapus customer"),
    ("content:read",            "read",   "content",         "Lihat konten"),
    ("content:create",          "create", "content",         "Buat konten"),
    ("content:update",          "update", "content",         "Edit konten"),
    ("content:delete",          "delete", "content",         "Hapus konten"),
    ("couriers:read",           "read",   "couriers",        "Lihat kurir"),
    ("couriers:create",         "create", "couriers",        "Tambah kurir"),
    ("couriers:update",         "update", "couriers",        "Edit kurir"),
    ("couriers:delete",         "delete", "couriers",        "Hapus kurir"),
    ("inventory:read",          "read",   "inventory",       "Lihat inventory"),
    ("inventory:create",        "create", "inventory",       "Tambah inventory"),
    ("payment-methods:read",    "read",   "payment-methods", "Lihat metode bayar"),
    ("payment-methods:create",  "create", "payment-methods", "Tambah metode bayar"),
    ("payment-methods:update",  "update", "payment-methods", "Edit metode bayar"),
    ("payment-methods:delete",  "delete", "payment-methods", "Hapus metode bayar"),
    ("reviews:read",            "read",   "reviews",         "Lihat review"),
    ("reviews:create",          "create", "reviews",         "Buat review"),
    ("reviews:update",          "update", "reviews",         "Edit review"),
    ("reviews:delete",          "delete", "reviews",         "Hapus review"),
    ("stores:read",             "read",   "stores",          "Lihat toko"),
    ("stores:create",           "create", "stores",          "Buat toko"),
    ("stores:update",           "update", "stores",          "Edit toko"),
    ("stores:delete",           "delete", "stores",          "Hapus toko"),
    ("vouchers:read",           "read",   "vouchers",        "Lihat voucher"),
    ("vouchers:create",         "create", "vouchers",        "Buat voucher"),
    ("vouchers:update",         "update", "vouchers",        "Edit voucher"),
    ("vouchers:delete",         "delete", "vouchers",        "Hapus voucher"),
]

ROLES = [
    {
        "name": "Admin",
        "slug": "admin",
        "description": "Full access ke semua fitur sistem",
        "is_system": True,
        # semua permissions
        "permissions": [p[0] for p in ALL_PERMISSIONS],
    },
    {
        "name": "Customer",
        "slug": "customer",
        "description": "Akses customer: belanja, lihat produk, kelola pesanan sendiri",
        "is_system": True,
        # permissions yang relevan untuk customer
        "permissions": [
            "products:read",
            "categories:read",
            "orders:read",
            "orders:create",
            "orders:update",
            "add_to_cart:read",
            "add_to_cart:create",
            "add_to_cart:update",
            "add_to_cart:delete",
            "customers:read",
            "customers:update",
            "content:read",
            "couriers:read",
            "payment-methods:read",
            "reviews:read",
            "reviews:create",
            "reviews:update",
            "stores:read",
            "vouchers:read",
        ],
    },
]

DEFAULT_USER_ROLE_SLUG = "customer"


# =============================================================================
# SEED LOGIC
# =============================================================================

async def seed():
    async with async_session() as db:
        print("=== Seed RBAC dimulai ===\n")

        # --- 1. Upsert permissions ---
        perm_id_map: dict[str, int] = {}
        for name, action, subject, desc in ALL_PERMISSIONS:
            row = await db.execute(
                text("SELECT id FROM rbac_permissions WHERE name = :name"),
                {"name": name},
            )
            existing = row.fetchone()
            if existing:
                perm_id_map[name] = existing[0]
                print(f"  [SKIP] permission '{name}' sudah ada (id={existing[0]})")
            else:
                result = await db.execute(
                    text(
                        "INSERT INTO rbac_permissions (name, action, subject, description, is_active, created_at, updated_at) "
                        "VALUES (:name, :action, :subject, :desc, true, NOW(), NOW()) RETURNING id"
                    ),
                    {"name": name, "action": action, "subject": subject, "desc": desc},
                )
                new_id = result.fetchone()[0]
                perm_id_map[name] = new_id
                print(f"  [OK]   permission '{name}' dibuat (id={new_id})")

        print(f"\n  Total permissions: {len(perm_id_map)}\n")

        # --- 2. Upsert roles ---
        role_id_map: dict[str, int] = {}
        for role_def in ROLES:
            row = await db.execute(
                text("SELECT id FROM rbac_roles WHERE slug = :slug"),
                {"slug": role_def["slug"]},
            )
            existing = row.fetchone()
            if existing:
                role_id_map[role_def["slug"]] = existing[0]
                print(f"  [SKIP] role '{role_def['slug']}' sudah ada (id={existing[0]})")
            else:
                result = await db.execute(
                    text(
                        "INSERT INTO rbac_roles (name, slug, description, is_system, is_active, created_at, updated_at) "
                        "VALUES (:name, :slug, :desc, :is_system, true, NOW(), NOW()) RETURNING id"
                    ),
                    {
                        "name": role_def["name"],
                        "slug": role_def["slug"],
                        "desc": role_def["description"],
                        "is_system": role_def["is_system"],
                    },
                )
                new_id = result.fetchone()[0]
                role_id_map[role_def["slug"]] = new_id
                print(f"  [OK]   role '{role_def['slug']}' dibuat (id={new_id})")

        print()

        # --- 3. Assign permissions ke role ---
        for role_def in ROLES:
            role_id = role_id_map[role_def["slug"]]
            for perm_name in role_def["permissions"]:
                perm_id = perm_id_map.get(perm_name)
                if not perm_id:
                    print(f"  [WARN] permission '{perm_name}' tidak ditemukan, skip")
                    continue
                row = await db.execute(
                    text(
                        "SELECT 1 FROM rbac_role_permissions "
                        "WHERE role_id = :rid AND permission_id = :pid"
                    ),
                    {"rid": role_id, "pid": perm_id},
                )
                if row.fetchone():
                    pass  # sudah ada, skip
                else:
                    await db.execute(
                        text(
                            "INSERT INTO rbac_role_permissions (role_id, permission_id, granted_at) "
                            "VALUES (:rid, :pid, NOW())"
                        ),
                        {"rid": role_id, "pid": perm_id},
                    )
            print(f"  [OK]   permissions untuk role '{role_def['slug']}' sudah di-assign")

        print()

        # --- 4. Assign default role 'customer' ke semua user non-superuser yang belum punya role ---
        customer_role_id = role_id_map.get(DEFAULT_USER_ROLE_SLUG)
        if customer_role_id:
            rows = await db.execute(
                text(
                    "SELECT id, email FROM users "
                    "WHERE is_superuser = false AND deleted_at IS NULL "
                    "AND id NOT IN (SELECT user_id FROM rbac_user_roles)"
                )
            )
            users_without_role = rows.fetchall()
            for user_id, email in users_without_role:
                await db.execute(
                    text(
                        "INSERT INTO rbac_user_roles (user_id, role_id, assigned_at) "
                        "VALUES (:uid, :rid, NOW())"
                    ),
                    {"uid": user_id, "rid": customer_role_id},
                )
                print(f"  [OK]   role 'customer' di-assign ke user '{email}'")
            if not users_without_role:
                print("  [INFO] Semua user sudah punya role, tidak ada yang perlu di-assign")

        await db.commit()
        print("\n=== Seed RBAC selesai ✅ ===")


if __name__ == "__main__":
    asyncio.run(seed())
