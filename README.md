# Business Intelligence Dashboard Proyek ETL & Analytics

Aplikasi dashboard Business Intelligence (BI) berbasis web yang dibangun menggunakan **Streamlit**. Proyek ini mengintegrasikan proses ETL (Extraction, Transformation, Loading) data dari file CSV ke database MySQL, melakukan analisis prediktif dengan Machine Learning (Regresi Linear), serta menyajikan visualisasi data yang interaktif.

---

## Struktur Direktori Utama

```text
project-bi/
│
├── app.py                 # Entry point utama aplikasi (UI dashboard & navigasi)
├── requirements.txt       # Daftar library python (pandas, streamlit, dll)
├── .env                   # Kredensial database MySQL yang aman
│
├── data/                  # Direktori untuk menyimpan CSV yang diunggah
│                  
├── core/
│   └── database.py        # Konfigurasi engine SQLAlchemy untuk koneksi MySQL
│
└── modules/
    ├── etl.py             # Fungsi ekstraksi CSV, pembersihan data, & load ke DB
    ├── ml_model.py        # Logika regresi linear sederhana menggunakan scikit-learn
    └── visualization.py   # Fungsi-fungsi pembuat grafik interaktif (Plotly)
```

## Prerequisites
- Python Version: `3.14.4`
- Database: `MySQL`

## Langkah-Langkah Setup Environment & Menjalankan Proyek
1. Clone repository ini di perangkat masing-masing
2. Membuat Virtual Environment (venv) bernama demo_etl melalui terminal powershell di vscode:
```bash
python -m venv demo_etl
```
3. Mengaktifkan Virtual Environment:
```bash
.\demo_etl\Scripts\Activate.ps1
```
4. Menginstal Dependensi (Library)
```bash
pip install -r requirements.txt
```
5. Verifikasi Instalasi untuk memastikan semua libary telah terinstal dan versinya sesuai:
```bash
pip freeze
```

## Konfigurasi Environment (.env)
Buat sebuah file bernama .env di direktori utama proyek, lalu sesuaikan dengan kredensial database MySQL masing-masing:
 ```bash
DB_HOST=localhost
DB_USER=user_anda
DB_PASSWORD=password_anda
DB_NAME=nama_database_anda
DB_PORT=3306
```