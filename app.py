# Entry point utama aplikasi (UI dashboard & navigasi)
import streamlit as st
import pandas as pd
import os
import plotly.express as px
from modules.etl import extract_data, transform_data, load_data
from core.database import get_engine
from modules.ml_model import run_revenue_prediction

# 1. Konfigurasi Halaman Web
st.set_page_config(page_title="BI Dashboard", layout="wide")

# Membuat folder 'data' otomatis jika belum ada
os.makedirs("data", exist_ok=True)

# Inisialisasi session_state untuk menyimpan status ETL
if 'etl_done' not in st.session_state:
    st.session_state.etl_done = False

# ==========================================
# HALAMAN 1: UPLOAD & ETL PROCESS
# ==========================================
if not st.session_state.etl_done:
    st.title("📂 Upload Dataset Business Intelligence")
    st.write("Silakan unggah file CSV Anda untuk memulai proses ETL dan menampilkan Dashboard.")
    
    # Widget Upload File
    uploaded_file = st.file_uploader("Pilih file CSV", type=['csv'])
    
    if uploaded_file is not None:
        if st.button("Mulai Proses ETL"):
            # Menyimpan file yang diunggah ke folder data/
            file_path = os.path.join("data", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Menampilkan animasi loading saat proses ETL berjalan
            with st.spinner("Proses ETL sedang berjalan... Mohon tunggu."):
                target_table = 'superstore_retail' # Nama tabel tujuan, editable
                
                # Menjalankan fungsi dari modul ETL yang sudah kamu buat
                raw_df = extract_data(file_path)
                if raw_df is not None:
                    cleaned_df = transform_data(raw_df)
                    load_data(cleaned_df, target_table)
                    
                    # Jika berhasil, ubah status session dan reload halaman
                    st.session_state.etl_done = True
                    st.success("ETL Selesai! Mengarahkan ke Dashboard...")
                    st.rerun()

# ==========================================
# HALAMAN 2: DASHBOARD BI
# ==========================================
else:
    st.title("📊 Business Intelligence Dashboard")
    st.write("Data telah berhasil dimuat dari database.")
    
    # Tombol untuk reset / unggah data baru
    if st.sidebar.button("Unggah Data Baru"):
        st.session_state.etl_done = False
        st.rerun()
        
    # Menarik data dari MySQL untuk divisualisasikan
    engine = get_engine()
    try:
        # Kita baca data yang sudah bersih dari database
        df_dashboard = pd.read_sql("SELECT * FROM superstore_retail", con=engine)
        
        # --- FITUR FILTER (di Sidebar) ---
        st.sidebar.header("Filter Data")
        
        # Simpan data asli ke df_base
        df_base = pd.read_sql("SELECT * FROM superstore_retail", con=engine)
        
        # 1. Filter Kategori (Berlaku untuk SEMUA)
        if 'category' in df_base.columns:
            kategori_pilihan = st.sidebar.multiselect(
                "Pilih Kategori Produk:",
                options=df_base['category'].unique(),
                default=df_base['category'].unique()
            )
            df_base = df_base[df_base['category'].isin(kategori_pilihan)]

        # 2. Filter Bulan
        if 'order_month' in df_base.columns:
            list_bulan = sorted(df_base['order_month'].unique(), reverse=True)
            
            bulan_pilihan = st.sidebar.selectbox(
                "Pilih Bulan (Berlaku untuk KPI 3 & Chart):", 
                options=["Semua Bulan"] + list_bulan
            )
        
        # --- LOGIKA PEMISAHAN DATAFRAME ---
        # Jika user memilih bulan spesifik, buat df_filtered untuk merender Chart & KPI 1 dan 3
        if bulan_pilihan != "Semua Bulan":
            df_filtered = df_base[df_base['order_month'] == bulan_pilihan]
        else:
            df_filtered = df_base
            
        # --- VISUALISASI KPI ---
        st.subheader("Key Performance Indicators (KPI)")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Mengikuti filter bulan (df_filtered)
            total_transaksi = len(df_filtered)
            st.metric(label="Total Transaksi", value=total_transaksi)
            
        with col2:
            # Selalu All-Time, jadi menggunakan data utama (df_base)
            if 'sales' in df_base.columns:
                total_revenue_all = df_base['sales'].sum()
                st.metric(label="Total Revenue (All Time)", value=f"${total_revenue_all:,.2f}")
                
        with col3:
            # Mengikuti filter bulan (df_filtered)
            if 'sales' in df_filtered.columns:
                revenue_bulan = df_filtered['sales'].sum()
                label_kpi3 = f"Revenue ({bulan_pilihan})" if bulan_pilihan != "Semua Bulan" else "Revenue (Semua Bulan)"
                st.metric(label=label_kpi3, value=f"${revenue_bulan:,.2f}")

        st.divider()

        # --- PERFORMANCE CHARTS ---
        st.subheader("Visualisasi Data")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # KUNCI PERBAIKAN: Gunakan df_filtered di sini
            if 'category' in df_filtered.columns:
                kat_count = df_filtered['category'].value_counts().reset_index()
                kat_count.columns = ['Kategori', 'Jumlah']
                
                fig_bar = px.bar(kat_count, x='Kategori', y='Jumlah', 
                                 title="Penjualan Berdasarkan Kategori",
                                 color='Kategori')
                st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            # KUNCI PERBAIKAN: Gunakan df_filtered di sini
            if 'segment' in df_filtered.columns:
                segment_count = df_filtered['segment'].value_counts().reset_index()
                segment_count.columns = ['Customer', 'Jumlah']
                
                fig_pie = px.pie(segment_count, names='Customer', values='Jumlah', 
                                 title="Segmentasi Customer")
                st.plotly_chart(fig_pie, use_container_width=True)
        
        # --- PREDIKSI MACHINE LEARNING ---
        st.divider()
        st.subheader("Analisis Prediktif (Machine Learning)")
        
        # Jalankan fungsi prediksi dengan melempar data df_dashboard yang sudah ditarik dari database
        # (Catatan: Kita pastikan melempar data sebelum terkena filter kategori di sidebar, 
        # agar prediksi selalu menggunakan seluruh data pendapatan perusahaan)
        
        # Tarik ulang data khusus untuk ML jika df_dashboard sudah terlanjur difilter di baris atas
        df_for_ml = pd.read_sql("SELECT order_month, sales FROM superstore_retail", con=engine)
        
        # Generate grafik prediksi
        fig_prediksi = run_revenue_prediction(df_for_ml)
        
        # Tampilkan grafik di Streamlit
        st.plotly_chart(fig_prediksi, use_container_width=True)
    except Exception as e:
        st.error(f"Gagal memuat data dari database. Error: {e}")