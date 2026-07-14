from fastcrud import FastCRUD

from .models import Courier, ShippingAddress

crud_couriers: FastCRUD = FastCRUD(Courier)
crud_shipping_addresses: FastCRUD = FastCRUD(ShippingAddress)
