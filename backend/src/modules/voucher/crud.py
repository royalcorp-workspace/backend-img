from fastcrud import FastCRUD

from .models import Voucher

crud_vouchers: FastCRUD = FastCRUD(Voucher, is_deleted_column="is_deleted")

