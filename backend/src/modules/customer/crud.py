from fastcrud import FastCRUD

from .models import Address, Customer

crud_customers: FastCRUD = FastCRUD(Customer)
crud_addresses: FastCRUD = FastCRUD(Address)
