# File: core/database.py
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Memuat variabel lingkungan dari file .env
load_dotenv()

# Mengambil kredensial dari environment variable
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')       
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')

# Membuat URL koneksi khusus untuk SQLAlchemy & PyMySQL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

def get_engine():
    """Fungsi untuk membuat dan mengembalikan engine koneksi database."""
    engine = create_engine(DATABASE_URL)
    return engine