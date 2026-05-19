# Konfigurasi engine SQLAlchemy untuk koneksi MySQL
from sqlalchemy import create_engine

DB_USER = 'root'
DB_PASSWORD = ''       
DB_HOST = 'localhost'
DB_NAME = 'kba'

# Membuat URL koneksi khusus untuk SQLAlchemy & PyMySQL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

def get_engine():
    """Fungsi untuk membuat dan mengembalikan engine koneksi database."""
    engine = create_engine(DATABASE_URL)
    return engine