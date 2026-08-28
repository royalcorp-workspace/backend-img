from fastcrud import FastCRUD

from .models import Review

crud_reviews: FastCRUD = FastCRUD(Review, is_deleted_column="is_deleted")
