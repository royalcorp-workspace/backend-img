from fastcrud import FastCRUD

from .models import Courier, ShippingAddress

crud_couriers: FastCRUD = FastCRUD(Courier, is_deleted_column="deleted")
crud_shipping_addresses: FastCRUD = FastCRUD(ShippingAddress, is_deleted_column="deleted")
