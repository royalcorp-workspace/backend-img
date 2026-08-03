from fastcrud import FastCRUD

from .models import AddToCart, AddToCartItem

crud_add_to_carts: FastCRUD = FastCRUD(AddToCart)
crud_add_to_cart_items: FastCRUD = FastCRUD(AddToCartItem)
