from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..common.schemas import TimestampSchema
from ..common.utils import get_media_url


class ProductBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=150)]
    slug: Annotated[str, Field(min_length=1, max_length=150, pattern=r"^[a-z0-9-]+$")]
    category_id: UUID | None = None
    brand_id: UUID | None = None
    thumbnail: str | None = None
    alt_text: str | None = None
    short_description: str | None = None
    description: str | None = None
    best_seller: bool = False
    is_new: bool = False
    is_bundle: bool = False
    status: int = 1
    uom: str | None = None
    segments: list[Any] | dict[str, Any] | None = None
    code: str | None = None
    warranty_duration: str | None = None
    courier_type: str | None = "keduanya"
    courier_type_label: str | None = None
    shipping_scheme: str | None = "dimension"
    shipping_scheme_label: str | None = None
    shipping_cost: float | None = 0.0
    length: str | None = None
    width: str | None = None
    height: str | None = None
    weight: str | None = None

    @field_validator("thumbnail", mode="before")
    @classmethod
    def format_thumbnail(cls, v: Any) -> Any:
        return get_media_url(v)


class Product(ProductBase, TimestampSchema):
    id: UUID
    images: list[dict[str, Any]] = []
    variants: list[dict[str, Any]] = []
    grouped_variants: list[dict[str, Any]] = []
    attribute_groups: dict[str, Any] = {}
    colors: list[dict[str, Any]] = []
    price_product_settings: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []
    avg_rating: float = 0.0
    total_reviews: int = 0

    @field_validator("images", mode="before")
    @classmethod
    def format_images(cls, v: Any) -> Any:
        if isinstance(v, list):
            formatted = []
            for item in v:
                if isinstance(item, dict):
                    item_copy = dict(item)
                    if "image" in item_copy:
                        item_copy["image"] = get_media_url(item_copy["image"])
                    if "image_url" in item_copy:
                        item_copy["image_url"] = get_media_url(item_copy["image_url"])
                    formatted.append(item_copy)
                elif isinstance(item, str):
                    formatted_url = get_media_url(item)
                    formatted.append({"image": formatted_url, "image_url": formatted_url})
                else:
                    formatted.append(item)
            return formatted
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    category_id: UUID | None = None
    brand_id: UUID | None = None
    thumbnail: str | None = None
    alt_text: str | None = None
    short_description: str | None = None
    description: str | None = None
    best_seller: bool | None = None
    is_new: bool | None = None
    status: int | None = None
    uom: str | None = None
    segments: list[Any] | dict[str, Any] | None = None
    code: str | None = None
    warranty_duration: str | None = None
    courier_type: str | None = None
    shipping_scheme: str | None = None
    shipping_cost: float | None = None
    length: str | None = None
    width: str | None = None
    height: str | None = None
    weight: str | None = None


class ProductRead(ProductBase):
    id: UUID
    images: list[dict[str, Any]] = []
    variants: list[dict[str, Any]] = []
    grouped_variants: list[dict[str, Any]] = []
    attribute_groups: dict[str, Any] = {}
    colors: list[dict[str, Any]] = []
    price_product_settings: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []
    avg_rating: float = 0.0
    total_reviews: int = 0
    final_price: float = 0.0
    tag_ids: list[str] = []
    tags: list[dict[str, Any]] = []

    @field_validator("images", mode="before")
    @classmethod
    def format_images_read(cls, v: Any) -> Any:
        if isinstance(v, list):
            formatted = []
            for item in v:
                if isinstance(item, dict):
                    item_copy = dict(item)
                    if "image" in item_copy:
                        item_copy["image"] = get_media_url(item_copy["image"])
                    if "image_url" in item_copy:
                        item_copy["image_url"] = get_media_url(item_copy["image_url"])
                    formatted.append(item_copy)
                elif isinstance(item, str):
                    formatted_url = get_media_url(item)
                    formatted.append({"image": formatted_url, "image_url": formatted_url})
                else:
                    formatted.append(item)
            return formatted
        return v


class ProductImageBase(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    image: str
    alt_text: str | None = None

    @field_validator("image", mode="before")
    @classmethod
    def format_image(cls, v: Any) -> Any:
        return get_media_url(v)


class ProductImage(ProductImageBase, TimestampSchema):
    id: UUID


class ProductImageCreate(ProductImageBase):
    pass


class ProductImageRead(ProductImageBase):
    id: UUID


class ProductVariantBase(BaseModel):
    product_id: UUID
    sku: str | None = None
    variant_name: str | None = None
    width: float | None = 0.0
    length: float | None = 0.0
    height: float | None = 0.0
    weight: float | None = 0.0
    package_length: float | None = None
    package_width: float | None = None
    package_height: float | None = None
    package_weight: float | None = None
    base_price: float | None = 0.0
    sell_price: float | None = 0.0
    shipping_cost: float | None = 0.0
    stock_qty: int | None = 0
    attributes: dict | None = None
    size: str | None = None
    kelengkapan: str | None = None
    thickness: str | None = None
    tebal: str | None = None


class ProductVariant(ProductVariantBase, TimestampSchema):
    id: UUID
    price_product_settings: list[dict[str, Any]] = []


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantRead(ProductVariantBase):
    id: UUID
    price_product_settings: list[dict[str, Any]] = []
    final_price: float = 0.0


class ProductColorBase(BaseModel):
    product_id: UUID
    color_name: Annotated[str, Field(min_length=1, max_length=50)]
    color_code: str | None = None


class ProductColor(ProductColorBase, TimestampSchema):
    id: UUID


class ProductColorCreate(ProductColorBase):
    pass


class ProductColorRead(ProductColorBase):
    id: UUID

class ProductBundlingItemBase(BaseModel):
    product_id: UUID
    variant_id: UUID | None = None
    quantity: int = 1
    is_suggest: bool = False
    bundle_price: float | None = None
    discount_percent: float | None = None
    discount_nominal: float | None = None

class ProductBundlingItemRead(ProductBundlingItemBase):
    id: UUID
    bundling_id: UUID

class ProductBundlingBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    price: float = 0.0
    is_active: bool = True
    start_date: Any | None = None
    end_date: Any | None = None
    discount_type: str | None = None
    banner: str | None = None
    image_url: str | None = None

    @field_validator("banner", "image_url", mode="before")
    @classmethod
    def format_bundling_images(cls, v: Any) -> Any:
        return get_media_url(v)


class ProductBundlingRead(ProductBundlingBase):
    id: UUID
    items: list[ProductBundlingItemRead] = []


class ProductBundlingItemDetailRead(BaseModel):
    id: UUID
    bundling_id: UUID
    product_id: UUID
    variant_id: UUID | None = None
    product_name: str | None = None
    product_slug: str | None = None
    variant_name: str | None = None
    quantity: int = 1
    is_suggest: bool = False
    bundle_price: float | None = None
    discount_percent: float | None = None
    discount_nominal: float | None = None
    original_price: float = 0.0
    min_price: float | None = None
    max_price: float | None = None
    price_range_text: str | None = None
    image_url: str | None = None


class ProductBundlingDetailRead(ProductBundlingBase):
    id: UUID
    total_normal_price: float = 0.0
    discount_amount: float = 0.0
    discount_percent: float = 0.0
    items: list[ProductBundlingItemDetailRead] = []
    fixed_items: list[ProductBundlingItemDetailRead] = []
    suggest_items: list[ProductBundlingItemDetailRead] = []