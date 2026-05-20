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
                target_table = 'customer_shopping' # Nama tabel tujuan, editable
                
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
        df_dashboard = pd.read_sql("SELECT * FROM customer_shopping", con=engine)
        
        # --- FITUR FILTER (di Sidebar) ---
        st.sidebar.header("Filter Data")
        
        # Cek apakah kolom 'category' ada untuk dijadikan filter (sesuaikan dengan datamu)
        if 'category' in df_dashboard.columns:
            kategori_pilihan = st.sidebar.multiselect(
                "Pilih Kategori Produk:",
                options=df_dashboard['category'].unique(),
                default=df_dashboard['category'].unique()
            )
            # Terapkan filter pada DataFrame
            df_dashboard = df_dashboard[df_dashboard['category'].isin(kategori_pilihan)]
        
        # --- VISUALISASI KPI ---
        st.subheader("Key Performance Indicators (KPI)")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_transaksi = len(df_dashboard)
            st.metric(label="Total Transaksi", value=total_transaksi)
            
        with col2:
            if 'total_price' in df_dashboard.columns:
                total_revenue = df_dashboard['total_price'].sum()
                # Format ke angka desimal rapi
                st.metric(label="Total Revenue", value=f"₺{total_revenue:,.2f}")
            else:
                st.metric(label="Total Revenue", value="N/A")
                
        with col3:
            if 'gender' in df_dashboard.columns:
                jumlah_gender = df_dashboard['gender'].nunique()
                st.metric(label="Demografi Gender", value=jumlah_gender)
            else:
                st.metric(label="Demografi Gender", value="N/A")

        st.divider()

        # --- PERFORMANCE CHARTS ---
        st.subheader("Visualisasi Data")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            if 'category' in df_dashboard.columns:
                # Menghitung jumlah per kategori
                kat_count = df_dashboard['category'].value_counts().reset_index()
                kat_count.columns = ['Kategori', 'Jumlah']
                
                # Membuat Bar Chart dengan Plotly
                fig_bar = px.bar(kat_count, x='Kategori', y='Jumlah', 
                                 title="Penjualan Berdasarkan Kategori",
                                 color='Kategori')
                st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            if 'payment_method' in df_dashboard.columns:
                # Membuat Pie Chart dengan Plotly
                pay_count = df_dashboard['payment_method'].value_counts().reset_index()
                pay_count.columns = ['Metode Pembayaran', 'Jumlah']
                
                fig_pie = px.pie(pay_count, names='Metode Pembayaran', values='Jumlah', 
                                 title="Distribusi Metode Pembayaran")
                st.plotly_chart(fig_pie, use_container_width=True)
        
        # --- PREDIKSI MACHINE LEARNING ---
        st.divider()
        st.subheader("Analisis Prediktif (Machine Learning)")
        
        # Jalankan fungsi prediksi dengan melempar data df_dashboard yang sudah ditarik dari database
        # (Catatan: Kita pastikan melempar data sebelum terkena filter kategori di sidebar, 
        # agar prediksi selalu menggunakan seluruh data pendapatan perusahaan)
        
        # Tarik ulang data khusus untuk ML jika df_dashboard sudah terlanjur difilter di baris atas
        df_for_ml = pd.read_sql("SELECT invoice_month, total_price FROM customer_shopping", con=engine)
        
        # Generate grafik prediksi
        fig_prediksi = run_revenue_prediction(df_for_ml)
        
        # Tampilkan grafik di Streamlit
        st.plotly_chart(fig_prediksi, use_container_width=True)
    except Exception as e:
        st.error(f"Gagal memuat data dari database. Error: {e}")