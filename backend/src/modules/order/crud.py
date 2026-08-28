from fastcrud import FastCRUD

from .models import Order

crud_orders: FastCRUD = FastCRUD(Order, is_deleted_column="deleted")

