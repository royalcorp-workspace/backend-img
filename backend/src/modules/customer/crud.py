from fastcrud import FastCRUD

from .models import Address, Customer

crud_customers: FastCRUD = FastCRUD(Customer, is_deleted_column="deleted")
crud_addresses: FastCRUD = FastCRUD(Address, is_deleted_column="deleted")
