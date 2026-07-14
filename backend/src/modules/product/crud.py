from fastcrud import FastCRUD

from .models import Product, ProductColor, ProductImage, ProductVariant

crud_products: FastCRUD = FastCRUD(Product)
crud_images: FastCRUD = FastCRUD(ProductImage)
crud_variants: FastCRUD = FastCRUD(ProductVariant)
crud_colors: FastCRUD = FastCRUD(ProductColor)

