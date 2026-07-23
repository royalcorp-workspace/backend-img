from fastcrud import FastCRUD

from .models import Buffer, BufferItem

crud_buffers: FastCRUD = FastCRUD(Buffer)
crud_buffer_items: FastCRUD = FastCRUD(BufferItem)
