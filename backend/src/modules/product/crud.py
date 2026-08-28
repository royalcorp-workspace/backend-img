from fastcrud import FastCRUD

from .models import Product, ProductColor, ProductImage, ProductVariant

crud_products: FastCRUD = FastCRUD(Product, is_deleted_column="deleted")
crud_images: FastCRUD = FastCRUD(ProductImage, is_deleted_column="deleted")
crud_variants: FastCRUD = FastCRUD(ProductVariant, is_deleted_column="deleted")
crud_colors: FastCRUD = FastCRUD(ProductColor, is_deleted_column="deleted")

