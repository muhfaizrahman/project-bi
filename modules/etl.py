# Fungsi ekstraksi CSV, pembersihan data, & load ke DB
import pandas as pd
from core.database import get_engine

def extract_data(file_path):
    """
    EXTRACT: Membaca file CSV ke dalam memori sebagai DataFrame Pandas.
    """
    print(f"-> Memulai proses Extract dari: {file_path}")
    try:
        # Membaca dataset
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        print("Error: File CSV tidak ditemukan. Pastikan path-nya benar.")
        return None

def transform_data(df):
    """
    TRANSFORM: Membersihkan dan memformat data agar siap masuk ke database.
    """
    print("-> Memulai proses Transform...")
    
    # 1. Menghapus baris yang sepenuhnya duplikat
    df = df.drop_duplicates()
    
    # 2. Menangani missing values (Nilai kosong/NaN)
    # Di sini kita menghapus baris yang memiliki nilai kosong. 
    # Alternatif lain: df.fillna(0) untuk mengisi nilai kosong dengan angka 0.
    df = df.dropna()
    
    # 3. Standardisasi nama kolom (penting agar penamaan tabel di MySQL rapi)
    # Mengubah semua huruf menjadi kecil dan mengganti spasi dengan underscore
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    
    # 4. (Opsional) Mengamankan tipe data tanggal jika kolom invoice_date ada di dataset
    if 'invoice_date' in df.columns:
        # Pandas bisa mencoba mendeteksi format tanggal secara otomatis
        df['invoice_date'] = pd.to_datetime(df['invoice_date'], format='mixed', errors='coerce')
        # Hapus data yang format tanggalnya rusak/tidak terbaca
        df = df.dropna(subset=['invoice_date'])

    return df

def load_data(df, table_name):
    """
    LOAD: Menyimpan DataFrame yang sudah bersih ke dalam MySQL.
    """
    print(f"-> Memulai proses Load ke tabel '{table_name}' di database 'kba'...")
    engine = get_engine()
    
    try:
        # if_exists='replace': Akan menghapus tabel lama jika sudah ada dan membuat yang baru.
        # Jika ingin menambahkan data ke tabel yang sudah ada, ganti menjadi 'append'.
        df.to_sql(name=table_name, con=engine, if_exists='replace', index=False)
        print(f"SUKSES: Data berhasil dimuat ke database MySQL!")
    except Exception as e:
        print(f"Error saat Load data: {e}")