from fastapi import APIRouter

from ....infrastructure.auth.routes import router as auth_router
from ....modules.api_keys.routes import router as api_keys_router
from ....modules.category.routes import router as categories_router
from ....modules.content.routes import router as content_router
from ....modules.courier.routes import router as couriers_router
from ....modules.customer.routes import router as customers_router
from ....modules.inventory.routes import router as inventory_router
from ....modules.order.routes import router as orders_router
from ....modules.payment_method.routes import router as payment_methods_router
from ....modules.product.routes import router as products_router
from ....modules.rate_limit.routes import router as rate_limits_router
from ....modules.review.routes import router as reviews_router
from ....modules.store.routes import router as stores_router
from ....modules.tier.routes import router as tiers_router
from ....modules.user.routes import router as users_router
from ....modules.voucher.routes import router as vouchers_router
from ....modules.sync.routes import router as sync_router

router = APIRouter(prefix="/v1")
router.include_router(users_router, prefix="/users")
router.include_router(tiers_router, prefix="/tiers")
router.include_router(rate_limits_router, prefix="/rate-limits")
router.include_router(auth_router, prefix="/auth")
router.include_router(api_keys_router, prefix="/api-keys")
router.include_router(categories_router, prefix="/categories")
router.include_router(customers_router, prefix="/customers")
router.include_router(products_router, prefix="/products")
router.include_router(orders_router, prefix="/orders")
router.include_router(vouchers_router, prefix="/vouchers")
router.include_router(inventory_router, prefix="/inventory")
router.include_router(reviews_router, prefix="/reviews")
router.include_router(couriers_router, prefix="/couriers")
router.include_router(payment_methods_router, prefix="/payment-methods")
router.include_router(stores_router, prefix="/stores")
router.include_router(content_router, prefix="/content")
router.include_router(sync_router, prefix="/sync")
