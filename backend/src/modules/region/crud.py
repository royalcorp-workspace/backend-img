from fastcrud import FastCRUD
from .models import Province, City, SubDistrict

crud_provinces: FastCRUD = FastCRUD(Province, is_deleted_column="deleted")
crud_cities: FastCRUD = FastCRUD(City, is_deleted_column="deleted")
crud_sub_districts: FastCRUD = FastCRUD(SubDistrict, is_deleted_column="deleted")
