from fastcrud import FastCRUD

from .models import AddToCart, AddToCartItem

crud_add_to_carts: FastCRUD = FastCRUD(AddToCart, is_deleted_column="deleted")
crud_add_to_cart_items: FastCRUD = FastCRUD(AddToCartItem, is_deleted_column="deleted")
