# Entry point utama aplikasi (UI dashboard & navigasi)
# Import modul ETL yang sudah dibuat
from modules.etl import extract_data, transform_data, load_data

def run_etl_pipeline():
    # Definisikan path file CSV dan nama tabel tujuan
    csv_file_path = 'data/customer_shopping_data.csv' # Nanti diganti make tempat nerima import data
    target_table = 'customer_shopping' # Nama tabel yang akan terbuat di dalam database 'kba', editable

    print("=== MEMULAI PIPELINE ETL ===")
    
    # Langkah 1: EXTRACT
    raw_df = extract_data(csv_file_path)
    
    # Pastikan data berhasil ditarik sebelum lanjut
    if raw_df is not None:
        
        # Langkah 2: TRANSFORM
        cleaned_df = transform_data(raw_df)
        
        # Menampilkan sekilas 5 data teratas yang sudah bersih (Opsional untuk cek)
        print("Preview Data Bersih:")
        print(cleaned_df.head())
        
        # Langkah 3: LOAD
        load_data(cleaned_df, target_table)

    print("=== PIPELINE SELESAI ===")

if __name__ == '__main__':
    run_etl_pipeline()