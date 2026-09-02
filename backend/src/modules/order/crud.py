from fastcrud import FastCRUD

from .models import Order, VoidOrder

crud_orders: FastCRUD = FastCRUD(Order, is_deleted_column="deleted")
crud_void_orders: FastCRUD = FastCRUD(VoidOrder)


