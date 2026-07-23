import pytest
from sqlalchemy import select

from src.modules.category.models import Category
from src.modules.common.utils.jde import extract_jde_rowset, validate_and_log_jde_payload
from src.modules.product.models import Brand, Product, ProductVariant
from src.modules.product.sync import sync_products_data
from src.modules.sync.sync import (
    _extract_branches,
    normalize_rowset,
    sync_base_price_data,
    safe_float,
)


def test_normalize_rowset_item_branch_accepts_branches_key():
    payload = {"branches": [{"bu": "1", "cabang_code": "A", "stocking_type": "S", "program_id": "P"}]}
    rowset = normalize_rowset(payload, endpoint="item-branch")
    assert len(rowset) == 1
    assert rowset[0]["bu"] == "1"


def test_normalize_rowset_item_branch_accepts_stores_key():
    payload = {"stores": [{"bu": "1", "cabang_code": "A"}]}
    rowset = normalize_rowset(payload, endpoint="item-branch")
    assert len(rowset) == 1


def test_normalize_rowset_item_branch_falls_back_to_any_list_of_dicts():
    payload = {"unknown_key": [{"bu": "1", "cabang_code": "A"}]}
    rowset = normalize_rowset(payload, endpoint="item-branch")
    assert len(rowset) == 1


def test_normalize_rowset_customer_master_accepts_customers_key():
    payload = {"customers": [{"an8": "1", "name": "Test"}]}
    rowset = normalize_rowset(payload, endpoint="customer-master")
    assert len(rowset) == 1


def test_extract_branches_accepts_stores_instead_of_branches():
    payload = {"stores": [{"business_unit": "1", "cabang_code": "A", "stocking_type": "S", "program_id": "P"}]}
    branches = _extract_branches(payload)
    assert len(branches) == 1
    assert branches[0]["cabang_code"] == "A"


def test_extract_branches_accepts_flat_branch_items():
    payload = [{"business_unit": "1", "cabang_code": "A", "stocking_type": "S", "program_id": "P"}]
    branches = _extract_branches(payload)
    assert len(branches) == 1
    assert branches[0]["cabang_code"] == "A"


@pytest.mark.asyncio
async def test_base_price_sync_reads_from_prices_array(db_session):
    category = Category(name="Divan", slug="divan-base-price-test")
    brand = Brand(name="Royal Foam", slug="royal-foam-base-price-test")
    db_session.add_all([category, brand])
    await db_session.flush()

    product = Product(
        name="JDE Base Price Test Product",
        slug="jde-base-price-test-slug",
        description="Test product",
        status=1,
        category_id=category.id,
        brand_id=brand.id,
    )
    db_session.add(product)
    await db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku="KML002010011386S200200",
        variant_name="Test Variant",
        price=0.0,
    )
    db_session.add(variant)
    await db_session.commit()

    payload = {
        "data": [
            {
                "sku": "KML002010011386S200200",
                "prices": [
                    {
                        "business_unit": "18011",
                        "business_unit_desc": "CAM - Bandung - Matras",
                        "currency": "IDR",
                        "uom": "PC",
                        "effective_date": "2026-06-01",
                        "expired_date": "2040-12-31",
                        "base_price": 7750000.0,
                        "user_id": "4879IRENES",
                        "program_id": "EP4106",
                        "date_update": "2026-05-13",
                        "time_of_day": 90028,
                    }
                ],
            }
        ]
    }

    result = await sync_base_price_data(db_session, payload)

    assert result["updated_variants"] == 1
    assert result["not_found_variants"] == 0

    await db_session.refresh(variant)
    assert variant.price == 7750000.0, (
        f"Expected variant.price=7750000.0 from prices[0].base_price, got {variant.price}"
    )


@pytest.mark.asyncio
async def test_base_price_sync_fallback_to_item_base_price(db_session):
    category = Category(name="Divan", slug="divan-base-price-fallback")
    brand = Brand(name="Royal Foam", slug="royal-foam-base-price-fallback")
    db_session.add_all([category, brand])
    await db_session.flush()

    product = Product(
        name="Fallback Product",
        slug="fallback-slug",
        description="Test product",
        status=1,
        category_id=category.id,
        brand_id=brand.id,
    )
    db_session.add(product)
    await db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku="TESTFALLBACKSKU",
        variant_name="Test Variant",
        price=0.0,
    )
    db_session.add(variant)
    await db_session.commit()

    payload = {
        "data": [
            {
                "sku": "TESTFALLBACKSKU",
                "base_price": 12345.0,
            }
        ]
    }

    result = await sync_base_price_data(db_session, payload)

    assert result["updated_variants"] == 1
    await db_session.refresh(variant)
    assert variant.price == 12345.0


@pytest.mark.asyncio
async def test_product_sync_does_not_overwrite_variant_price_when_missing(db_session):
    category = Category(name="Divan", slug="divan-no-overwrite")
    brand = Brand(name="Royal Foam", slug="royal-foam-no-overwrite")
    db_session.add_all([category, brand])
    await db_session.flush()

    product = Product(
        name="Product No Overwrite",
        slug="no-overwrite-slug",
        description="Test product",
        status=1,
        category_id=category.id,
        brand_id=brand.id,
    )
    db_session.add(product)
    await db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku="NOOVER123",
        variant_name="Existing Variant",
        price=5500000.0,
    )
    db_session.add(variant)
    await db_session.commit()

    payload = {
        "rowset": [
            {
                "name": "Product No Overwrite",
                "slug": "no-overwrite-slug",
                "template": "Divan",
                "variants": [
                    {
                        "sku": "NOOVER123",
                        "variant_name": "Existing Variant",
                        "length": 200,
                        "width": 90,
                    }
                ],
            }
        ]
    }

    await sync_products_data(db_session, payload)

    await db_session.refresh(variant)
    assert variant.price == 5500000.0, (
        f"Product sync should not overwrite existing variant price. "
        f"Expected 5500000.0, got {variant.price}"
    )


@pytest.mark.asyncio
async def test_product_sync_updates_variant_price_when_provided(db_session):
    category = Category(name="Divan", slug="divan-update-price")
    brand = Brand(name="Royal Foam", slug="royal-foam-update-price")
    db_session.add_all([category, brand])
    await db_session.flush()

    product = Product(
        name="Product Update Price",
        slug="update-price-slug",
        description="Test product",
        status=1,
        category_id=category.id,
        brand_id=brand.id,
    )
    db_session.add(product)
    await db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku="UPDATEPRICE123",
        variant_name="Update Me",
        price=1000.0,
    )
    db_session.add(variant)
    await db_session.commit()

    payload = {
        "rowset": [
            {
                "name": "Product Update Price",
                "slug": "update-price-slug",
                "template": "Divan",
                "variants": [
                    {
                        "sku": "UPDATEPRICE123",
                        "variant_name": "Update Me",
                        "length": 200,
                        "width": 90,
                        "price": 2500000.0,
                    }
                ],
            }
        ]
    }

    await sync_products_data(db_session, payload)

    await db_session.refresh(variant)
    assert variant.price == 2500000.0


@pytest.mark.asyncio
async def test_product_sync_uses_base_price_for_new_variant_without_explicit_price(db_session):
    category = Category(name="Divan", slug="divan-new-variant-price")
    brand = Brand(name="Royal Foam", slug="royal-foam-new-variant-price")
    db_session.add_all([category, brand])
    await db_session.flush()

    product = Product(
        name="New Variant Price",
        slug="new-variant-price-slug",
        description="Test product",
        status=1,
        category_id=category.id,
        brand_id=brand.id,
        base_price="5000000",
    )
    db_session.add(product)
    await db_session.flush()

    payload = {
        "rowset": [
            {
                "name": "New Variant Price",
                "slug": "new-variant-price-slug",
                "template": "Divan",
                "base_price": 5000000.0,
                "variants": [
                    {
                        "sku": "NEWVAR456",
                        "variant_name": "New Variant",
                        "length": 180,
                        "width": 200,
                    }
                ],
            }
        ]
    }

    await sync_products_data(db_session, payload)

    stmt = select(ProductVariant).where(ProductVariant.sku == "NEWVAR456")
    res = await db_session.execute(stmt)
    new_variant = res.scalar_one_or_none()

    assert new_variant is not None
    assert new_variant.price == 5000000.0, (
        f"New variant should get product base_price={5000000.0}, got {new_variant.price}"
    )
