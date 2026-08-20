import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure.database.models import TimestampMixin
from ...infrastructure.database.session import Base

if TYPE_CHECKING:
    from ..review.models import Review


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_category.id"), index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id"), index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    thumbnail: Mapped[str | None] = mapped_column(String(255), default=None)
    alt_text: Mapped[str | None] = mapped_column(String(150), default=None)
    short_description: Mapped[str | None] = mapped_column(String(500), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    best_seller: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)
    creator: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    editor: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    base_price: Mapped[str | None] = mapped_column(String(255), default=None)
    uom: Mapped[str | None] = mapped_column(String(255), default=None)
    segments: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB, default=None)

    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage", back_populates="product", lazy="selectin", cascade="all, delete-orphan", init=False
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", lazy="selectin", cascade="all, delete-orphan", init=False
    )
    colors: Mapped[list["ProductColor"]] = relationship(
        "ProductColor", back_populates="product", lazy="selectin", cascade="all, delete-orphan", init=False
    )
    price_product_settings: Mapped[list["PriceProductSetting"]] = relationship(
        "PriceProductSetting",
        secondary="price_product_setting_items",
        back_populates="products",
        lazy="selectin",
        init=False,
        viewonly=True,
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="product", lazy="selectin", cascade="all, delete-orphan", init=False
    )
    suggestions: Mapped[list["Product"]] = relationship(
        "Product",
        secondary="product_suggestions",
        primaryjoin="Product.id==ProductSuggestion.product_id",
        secondaryjoin="Product.id==ProductSuggestion.suggested_product_id",
        order_by="ProductSuggestion.sort_order",
        lazy="selectin",
        init=False,
        viewonly=True,
    )


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(150), default=None)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    status: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped["Product"] = relationship("Product", back_populates="images", lazy="selectin", init=False)


class ProductSuggestion(Base):
    __tablename__ = "product_suggestions"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), primary_key=True)
    suggested_product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), default=None)
    variant_name: Mapped[str | None] = mapped_column("variant_name", String(100), default=None)
    price: Mapped[float | None] = mapped_column(default=0.0)
    stock_qty: Mapped[int | None] = mapped_column("stock_quantity", Integer, default=0)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    creator: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    editor: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    product: Mapped["Product"] = relationship("Product", back_populates="variants", lazy="selectin", init=False)
    price_product_settings: Mapped[list["PriceProductSetting"]] = relationship(
        "PriceProductSetting",
        secondary="price_product_setting_items",
        back_populates="variants",
        lazy="selectin",
        init=False,
        viewonly=True,
    )


class ProductColor(Base, TimestampMixin):
    __tablename__ = "product_colors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    color_name: Mapped[str] = mapped_column(String(50), nullable=False)
    color_code: Mapped[str | None] = mapped_column(String(20), default=None)
    creator: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    editor: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    product: Mapped["Product"] = relationship("Product", back_populates="colors", lazy="selectin", init=False)


class PriceProductSettingItem(Base):
    __tablename__ = "price_product_setting_items"

    price_product_setting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("price_product_settings.id"), primary_key=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), primary_key=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id"), primary_key=True, default=None)
    discount_type: Mapped[int | None] = mapped_column(Integer, default=None)
    discount_value: Mapped[float | None] = mapped_column(default=0.0)
    creator: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    editor: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    setting: Mapped["PriceProductSetting"] = relationship("PriceProductSetting", lazy="selectin", init=False)


class PriceProductSetting(Base, TimestampMixin):
    __tablename__ = "price_product_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    type: Mapped[int | None] = mapped_column(Integer, default=1)
    scope: Mapped[int | None] = mapped_column(Integer, default=1)
    discount_type: Mapped[int | None] = mapped_column(Integer, default=None)
    discount_value: Mapped[float | None] = mapped_column(default=0.0)
    min_purchase: Mapped[float | None] = mapped_column(default=0.0)
    max_discount: Mapped[float | None] = mapped_column(default=None)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    image_url: Mapped[str | None] = mapped_column(String(255), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)
    creator: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    editor: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)

    products: Mapped[list["Product"]] = relationship(
        "Product",
        secondary="price_product_setting_items",
        back_populates="price_product_settings",
        lazy="selectin",
        init=False,
        viewonly=True,
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        secondary="price_product_setting_items",
        back_populates="price_product_settings",
        lazy="selectin",
        init=False,
        viewonly=True,
    )
    volume_tiers: Mapped[list["VolumeTier"]] = relationship(
        "VolumeTier",
        back_populates="price_product_setting",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
    )


class VolumeTier(Base, TimestampMixin):
    __tablename__ = "price_product_setting_volume_tiers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    price_product_setting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("price_product_settings.id"), nullable=False)
    min_purchase: Mapped[int | None] = mapped_column(Integer, default=0)
    discount_type: Mapped[int | None] = mapped_column(Integer, default=1)
    discount_value: Mapped[int | None] = mapped_column(Integer, default=0)
    sort_order: Mapped[int | None] = mapped_column(Integer, default=0)

    price_product_setting: Mapped["PriceProductSetting"] = relationship(
        "PriceProductSetting", back_populates="volume_tiers", lazy="selectin", init=False
    )


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=1)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class RefProductCategory(Base, TimestampMixin):
    __tablename__ = "ref_product_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)


class ProductBundling(Base, TimestampMixin):
    __tablename__ = "products_bundling"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    price: Mapped[float] = mapped_column(default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    creator: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    editor: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    discount_type: Mapped[str | None] = mapped_column(String(50), default=None)
    banner: Mapped[str | None] = mapped_column(String(255), default=None)
    image_url: Mapped[str | None] = mapped_column(String(255), default=None)

    items: Mapped[list["ProductBundlingItem"]] = relationship(
        "ProductBundlingItem", back_populates="bundling", lazy="selectin", cascade="all, delete-orphan", init=False
    )


class ProductBundlingItem(Base, TimestampMixin):
    __tablename__ = "products_bundling_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    bundling_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products_bundling.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id"), default=None)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    bundling: Mapped["ProductBundling"] = relationship("ProductBundling", back_populates="items", init=False)
    product: Mapped["Product"] = relationship("Product", lazy="selectin", init=False)
    variant: Mapped["ProductVariant"] = relationship("ProductVariant", lazy="selectin", init=False)
