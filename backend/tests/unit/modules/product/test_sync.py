import uuid
import pytest
from sqlalchemy import select
from src.modules.category.models import Category
from src.modules.product.models import Product, Brand
from src.modules.product.sync import safe_float, slugify, sync_products_data


def test_slugify():
    assert slugify("DV (L1) HOTEL CLASSIC LH-8") == "dv-l1-hotel-classic-lh-8"
    assert slugify("ELITE MATTRESS PROTECTOR (NFS)") == "elite-mattress-protector-nfs"
    assert slugify("  test  name  ") == "test-name"
    assert slugify("special@#$characters") == "specialcharacters"


def test_safe_float():
    assert safe_float("200") == 200.0
    assert safe_float("090") == 90.0
    assert safe_float("  1,500.50  ") == 1500.50
    assert safe_float("") == 0.0
    assert safe_float("invalid") == 0.0
    assert safe_float(None) == 0.0


@pytest.mark.asyncio
async def test_sync_products_data_transaction_error(db_session):
    category = Category(name="Divan", slug="divan")
    brand = Brand(name="Royal Foam", slug="royal-foam")
    db_session.add(category)
    db_session.add(brand)
    await db_session.flush()

    deleted_product = Product(
        name="Deleted Product",
        slug="failed-slug",
        description="A deleted product",
        status=False,
        deleted=True,
        category_id=category.id,
        brand_id=brand.id,
    )
    db_session.add(deleted_product)
    await db_session.commit()

    # 2. Prepare payload
    payload = {
        "rowset": [
            {
                "name": "Failed Product Name",
                "slug": "failed-slug",  # matches the deleted product's slug -> unique violation on insert
                "template": "Divan",
            },
            {
                "name": "Success Product",
                "slug": "success-slug",
                "template": "Divan",
            }
        ]
    }

    # 3. Run sync
    results = await sync_products_data(db_session, payload)

    # 4. Check results
    assert results["failed_items"] == 1
    assert results["inserted_products"] == 1

    # 5. Verify the success product is inserted and saved
    stmt = select(Product).where(Product.slug == "success-slug")
    res = await db_session.execute(stmt)
    success_product = res.scalar_one_or_none()
    assert success_product is not None
    assert success_product.name == "Success Product"

