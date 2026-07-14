from fastcrud import FastCRUD

from .models import Voucher

crud_vouchers: FastCRUD = FastCRUD(Voucher)

