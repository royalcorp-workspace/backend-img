from typing import Annotated

from fastapi import Depends

from .service import ColorService, ImageService, ProductService, VariantService


def get_product_service() -> ProductService:
    return ProductService()


def get_image_service() -> ImageService:
    return ImageService()


def get_variant_service() -> VariantService:
    return VariantService()


def get_color_service() -> ColorService:
    return ColorService()


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]
VariantServiceDep = Annotated[VariantService, Depends(get_variant_service)]
ColorServiceDep = Annotated[ColorService, Depends(get_color_service)]
