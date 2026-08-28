from fastcrud import FastCRUD

from .models import Category

crud_categories: FastCRUD = FastCRUD(Category, is_deleted_column="deleted")

