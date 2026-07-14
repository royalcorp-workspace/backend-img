from fastcrud import FastCRUD

from .models import PaymentMethod

crud_payment_methods: FastCRUD = FastCRUD(PaymentMethod)
