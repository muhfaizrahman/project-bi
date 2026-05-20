# ============================================================
# Entry point utama aplikasi (UI dashboard & navigasi)
# Versi Interaktif: Tooltip, Cross-filtering, Dynamic Slicer
# ============================================================
import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from modules.etl import extract_data, transform_data, load_data
from core.database import get_engine
from modules.ml_model import run_revenue_prediction

# ============================================================
# 1. KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(page_title="BI Dashboard", layout="wide")

# CSS kustom: styling badge cross-filter & tombol reset
st.markdown("""
<style>
    /* Badge indikator cross-filter aktif */
    .crossfilter-badge {
        background: #1f77b4;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 8px;
    }
    /* Highlight metrik saat cross-filter aktif */
    div[data-testid="stMetric"] {
        background: #f0f6ff;
        border-radius: 8px;
        padding: 8px 12px;
        border-left: 3px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

os.makedirs("data", exist_ok=True)

# ============================================================
# 2. INISIALISASI SESSION STATE
# ============================================================
defaults = {
    'etl_done': False,
    # Cross-filter state — menyimpan nilai yang diklik user di tiap chart
    'cf_category': None,      # klik dari bar chart kategori
    'cf_segment': None,       # klik dari pie chart segmen
    'cf_sub_category': None,  # klik dari bar chart sub-kategori
    'cf_ship_mode': None,     # klik dari donut chart pengiriman
    'cf_state': None,         # klik dari choropleth map
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ============================================================
# HELPER: Fungsi terpusat untuk membaca klik Plotly
# ============================================================
def get_click_value(event_data, key_field='x'):
    """Mengekstrak nilai dari plotly click event (st.plotly_chart on_select)."""
    if event_data and event_data.get('selection') and event_data['selection'].get('points'):
        point = event_data['selection']['points'][0]
        return point.get(key_field) or point.get('label') or point.get('location')
    return None


# ============================================================
# HELPER: Terapkan semua cross-filter aktif ke dataframe
# ============================================================
def apply_crossfilters(df, exclude=None):
    """
    Terapkan semua filter aktif dari session_state ke df.
    exclude: nama kolom yang TIDAK difilter (supaya chart sumber tetap utuh).
    """
    exclude = exclude or []
    filtered = df.copy()

    mapping = {
        'category':     ('cf_category',     'category'),
        'segment':      ('cf_segment',       'segment'),
        'sub_category': ('cf_sub_category',  'sub_category'),
        'ship_mode':    ('cf_ship_mode',     'ship_mode'),
        'state':        ('cf_state',         'state'),
    }

    for col, (state_key, df_col) in mapping.items():
        if col in exclude:
            continue
        val = st.session_state.get(state_key)
        if val and df_col in filtered.columns:
            filtered = filtered[filtered[df_col] == val]

    return filtered


# ============================================================
# HELPER: Tampilkan badge cross-filter yang sedang aktif
# ============================================================
def render_crossfilter_badges():
    labels = {
        'cf_category':     'Kategori',
        'cf_segment':      'Segmen',
        'cf_sub_category': 'Sub-Kategori',
        'cf_ship_mode':    'Pengiriman',
        'cf_state':        'State',
    }
    aktif = {k: v for k, v in labels.items() if st.session_state.get(k)}
    if aktif:
        badges = " &nbsp; ".join(
            f'<span class="crossfilter-badge">🔗 {label}: {st.session_state[k]}</span>'
            for k, label in aktif.items()
        )
        st.markdown(badges, unsafe_allow_html=True)


# ============================================================
# HELPER: Reset semua cross-filter
# ============================================================
def reset_crossfilters():
    for key in ['cf_category', 'cf_segment', 'cf_sub_category', 'cf_ship_mode', 'cf_state']:
        st.session_state[key] = None


# ============================================================
# HELPER: Template tooltip kustom yang kaya informasi
# ============================================================
def make_hovertemplate_bar(x_label, y_label, extra_cols=None):
    """Buat hovertemplate standar untuk bar/horizontal bar."""
    tpl = (
        f"<b>%{{x}}</b><br>"
        f"{y_label}: <b>%{{y:,}}</b>"
    )
    if extra_cols:
        for col in extra_cols:
            tpl += f"<br>{col['label']}: <b>%{{customdata[{col['idx']}]}}</b>"
    tpl += "<extra></extra>"
    return tpl


# ============================================================
# HALAMAN 1: UPLOAD & ETL
# ============================================================
if not st.session_state.etl_done:
    st.title("Upload Dataset Business Intelligence")
    st.write("Silakan unggah file CSV Anda untuk memulai proses ETL dan menampilkan Dashboard.")

    uploaded_file = st.file_uploader("Pilih file CSV", type=['csv'])

    if uploaded_file is not None:
        if st.button("Mulai Proses ETL"):
            file_path = os.path.join("data", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("Proses ETL sedang berjalan... Mohon tunggu."):
                target_table = 'superstore_retail'
                raw_df = extract_data(file_path)
                if raw_df is not None:
                    cleaned_df = transform_data(raw_df)
                    load_data(cleaned_df, target_table)
                    st.session_state.etl_done = True
                    st.success("ETL Selesai! Mengarahkan ke Dashboard...")
                    st.rerun()


# ============================================================
# HALAMAN 2: DASHBOARD BI INTERAKTIF
# ============================================================
else:
    st.title("Business Intelligence Dashboard")

    # --- Sidebar: Navigasi & Reset ---
    st.sidebar.header("⚙️ Kontrol Dashboard")
    if st.sidebar.button("📂 Unggah Data Baru"):
        st.session_state.etl_done = False
        reset_crossfilters()
        st.rerun()

    engine = get_engine()

    try:
        # Tarik data sekali, simpan sebagai df_raw (tidak pernah dimodifikasi)
        df_raw = pd.read_sql("SELECT * FROM superstore_retail", con=engine)

        # =====================================================
        # SIDEBAR: SLICER / FILTER DINAMIS
        # =====================================================
        st.sidebar.markdown("---")
        st.sidebar.header("🔍 Filter Data (Slicer)")

        df_slicer = df_raw.copy()

        # --- Slicer 1: Kategori (multiselect) ---
        if 'category' in df_slicer.columns:
            all_cat = sorted(df_slicer['category'].unique())
            sel_cat = st.sidebar.multiselect(
                "Kategori Produk:", options=all_cat, default=all_cat,
                help="Pilih satu atau lebih kategori produk."
            )
            df_slicer = df_slicer[df_slicer['category'].isin(sel_cat)]

        # --- Slicer 2: Sub-Kategori (multiselect, dinamis mengikuti Kategori) ---
        if 'sub_category' in df_slicer.columns:
            all_subcat = sorted(df_slicer['sub_category'].unique())
            sel_subcat = st.sidebar.multiselect(
                "Sub-Kategori:", options=all_subcat, default=all_subcat,
                help="Daftar sub-kategori menyesuaikan pilihan Kategori di atas."
            )
            df_slicer = df_slicer[df_slicer['sub_category'].isin(sel_subcat)]

        # --- Slicer 3: Segmen Customer (multiselect) ---
        if 'segment' in df_slicer.columns:
            all_seg = sorted(df_slicer['segment'].unique())
            sel_seg = st.sidebar.multiselect(
                "Segmen Customer:", options=all_seg, default=all_seg
            )
            df_slicer = df_slicer[df_slicer['segment'].isin(sel_seg)]

        # --- Slicer 4: Rentang Tanggal (date_input) ---
        if 'order_date' in df_slicer.columns:
            df_slicer['order_date'] = pd.to_datetime(df_slicer['order_date'])
            min_date = df_slicer['order_date'].min().date()
            max_date = df_slicer['order_date'].max().date()

            st.sidebar.markdown("**Rentang Tanggal Order:**")
            date_start = st.sidebar.date_input("Dari tanggal:", value=min_date, min_value=min_date, max_value=max_date)
            date_end   = st.sidebar.date_input("Sampai tanggal:", value=max_date, min_value=min_date, max_value=max_date)

            if date_start <= date_end:
                df_slicer = df_slicer[
                    (df_slicer['order_date'].dt.date >= date_start) &
                    (df_slicer['order_date'].dt.date <= date_end)
                ]
            else:
                st.sidebar.warning("⚠️ Tanggal awal tidak boleh melebihi tanggal akhir.")

        # --- Slicer 5: Rentang Sales (slider) ---
        if 'sales' in df_slicer.columns:
            min_sales = float(df_slicer['sales'].min())
            max_sales = float(df_slicer['sales'].max())
            sales_range = st.sidebar.slider(
                "Rentang Nilai Sales ($):",
                min_value=min_sales, max_value=max_sales,
                value=(min_sales, max_sales),
                format="$%.0f"
            )
            df_slicer = df_slicer[
                (df_slicer['sales'] >= sales_range[0]) &
                (df_slicer['sales'] <= sales_range[1])
            ]

        # --- Slicer 6: Bulan (filter KPI) ---
        bulan_pilihan = "Semua Bulan"
        if 'order_month' in df_slicer.columns:
            list_bulan = sorted(df_slicer['order_month'].unique(), reverse=True)
            bulan_pilihan = st.sidebar.selectbox(
                "Pilih Bulan (KPI):",
                options=["Semua Bulan"] + list(list_bulan)
            )

        st.sidebar.markdown("---")
        # Tombol reset cross-filter
        cf_aktif = any(st.session_state.get(k) for k in
                       ['cf_category', 'cf_segment', 'cf_sub_category', 'cf_ship_mode', 'cf_state'])
        if cf_aktif:
            if st.sidebar.button("🔄 Reset Cross-Filter"):
                reset_crossfilters()
                st.rerun()

        # df_base = hasil slicer sidebar, sebelum cross-filter chart
        df_base = df_slicer.copy()

        # df_filtered = df_base + filter bulan
        if bulan_pilihan != "Semua Bulan" and 'order_month' in df_base.columns:
            df_month = df_base[df_base['order_month'] == bulan_pilihan]
        else:
            df_month = df_base.copy()

        # =====================================================
        # INDIKATOR CROSS-FILTER AKTIF
        # =====================================================
        render_crossfilter_badges()
        if cf_aktif:
            st.caption("💡 Klik area kosong pada grafik untuk mereset cross-filter, atau gunakan tombol di sidebar.")

        # =====================================================
        # KPI CARDS
        # =====================================================
        st.subheader("📊 Key Performance Indicators (KPI)")

        # Terapkan cross-filter ke df_month untuk KPI
        df_kpi = apply_crossfilters(df_month)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Transaksi", f"{len(df_kpi):,}")

        with col2:
            if 'sales' in df_base.columns:
                rev_all = apply_crossfilters(df_base)['sales'].sum()
                st.metric("Revenue (All Time)", f"${rev_all:,.2f}")

        with col3:
            if 'sales' in df_kpi.columns:
                label_kpi3 = f"Revenue ({bulan_pilihan})" if bulan_pilihan != "Semua Bulan" else "Revenue (Semua Bulan)"
                st.metric(label_kpi3, f"${df_kpi['sales'].sum():,.2f}")

        with col4:
            if 'profit' in df_kpi.columns:
                st.metric("Total Profit", f"${df_kpi['profit'].sum():,.2f}")
            elif 'sales' in df_kpi.columns and len(df_kpi) > 0:
                avg_sales = df_kpi['sales'].mean()
                st.metric("Rata-rata Sales/Transaksi", f"${avg_sales:,.2f}")

        st.divider()

        # =====================================================
        # BARIS 1: BAR KATEGORI + PIE SEGMEN
        # =====================================================
        st.subheader("📈 Visualisasi Data Interaktif")
        st.caption("Klik elemen grafik manapun untuk mengaktifkan cross-filter ke semua grafik lainnya.")

        chart_col1, chart_col2 = st.columns(2)

        # --- [CHART 1] Bar Chart: Penjualan per Kategori ---
        with chart_col1:
            if 'category' in df_base.columns and 'sales' in df_base.columns:
                # Cross-filter: chart ini dikecualikan dari filter cf_category-nya sendiri
                df_c1 = apply_crossfilters(df_month, exclude=['category'])

                kat_data = (
                    df_c1.groupby('category')
                    .agg(
                        Jumlah_Transaksi=('sales', 'count'),
                        Total_Sales=('sales', 'sum'),
                        Avg_Sales=('sales', 'mean')
                    )
                    .reset_index()
                    .rename(columns={'category': 'Kategori'})
                )

                # Tandai bar yang dipilih (highlight)
                selected_cat = st.session_state.get('cf_category')
                kat_data['_selected'] = kat_data['Kategori'].apply(
                    lambda x: 1.0 if (selected_cat is None or x == selected_cat) else 0.4
                )

                fig_bar = go.Figure()
                for _, row in kat_data.iterrows():
                    fig_bar.add_trace(go.Bar(
                        x=[row['Kategori']],
                        y=[row['Jumlah_Transaksi']],
                        name=row['Kategori'],
                        opacity=row['_selected'],
                        # Tooltip kaya informasi
                        customdata=[[row['Total_Sales'], row['Avg_Sales']]],
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "Jumlah Transaksi: <b>%{y:,}</b><br>"
                            "Total Sales: <b>$%{customdata[0]:,.2f}</b><br>"
                            "Rata-rata Sales: <b>$%{customdata[1]:,.2f}</b>"
                            "<extra></extra>"
                        ),
                    ))

                fig_bar.update_layout(
                    title="Penjualan Berdasarkan Kategori",
                    showlegend=True,
                    barmode='group',
                    xaxis_title="Kategori",
                    yaxis_title="Jumlah Transaksi",
                    hovermode='x unified',
                )

                # on_select: tangkap klik user → simpan ke session_state → rerun
                event_bar = st.plotly_chart(
                    fig_bar, use_container_width=True,
                    on_select="rerun", key="chart_category"
                )
                clicked_cat = get_click_value(event_bar, 'x')
                if clicked_cat:
                    # Toggle: klik ulang nilai yang sama → reset filter
                    if st.session_state.cf_category == clicked_cat:
                        st.session_state.cf_category = None
                    else:
                        st.session_state.cf_category = clicked_cat
                    st.rerun()

        # --- [CHART 2] Pie Chart: Segmentasi Customer ---
        with chart_col2:
            if 'segment' in df_base.columns:
                df_c2 = apply_crossfilters(df_month, exclude=['segment'])

                seg_data = (
                    df_c2.groupby('segment')
                    .agg(
                        Jumlah=('segment', 'count'),
                        Total_Sales=('sales', 'sum') if 'sales' in df_c2.columns else ('segment', 'count')
                    )
                    .reset_index()
                    .rename(columns={'segment': 'Customer'})
                )

                selected_seg = st.session_state.get('cf_segment')
                pull_values = [
                    0.1 if (selected_seg and row['Customer'] == selected_seg) else 0
                    for _, row in seg_data.iterrows()
                ]

                fig_pie = go.Figure(go.Pie(
                    labels=seg_data['Customer'],
                    values=seg_data['Jumlah'],
                    pull=pull_values,
                    customdata=seg_data['Total_Sales'] if 'Total_Sales' in seg_data.columns else seg_data['Jumlah'],
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Jumlah Customer: <b>%{value:,}</b><br>"
                        "Persentase: <b>%{percent}</b><br>"
                        "Total Sales: <b>$%{customdata:,.2f}</b>"
                        "<extra></extra>"
                    ),
                    textinfo='label+percent',
                ))
                fig_pie.update_layout(title="Segmentasi Customer")

                event_pie = st.plotly_chart(
                    fig_pie, use_container_width=True,
                    on_select="rerun", key="chart_segment"
                )
                clicked_seg = get_click_value(event_pie, 'label')
                if clicked_seg:
                    if st.session_state.cf_segment == clicked_seg:
                        st.session_state.cf_segment = None
                    else:
                        st.session_state.cf_segment = clicked_seg
                    st.rerun()

        # =====================================================
        # BARIS 2: SUB-KATEGORI + PENGIRIMAN
        # =====================================================
        # --- BARIS PERTAMA (2 Kolom): Sub-Kategori & Mode Pengiriman ---
        col1, col2 = st.columns(2)

        # --- [CHART 1] Horizontal Bar: Sub-Kategori ---
        with col1:
            if 'sub_category' in df_base.columns:
                df_c3 = apply_crossfilters(df_month, exclude=['sub_category'])

                sub_data = (
                    df_c3.groupby('sub_category')
                    .agg(
                        Jumlah=('sub_category', 'count'),
                        Total_Sales=('sales', 'sum') if 'sales' in df_c3.columns else ('sub_category', 'count'),
                        Avg_Sales=('sales', 'mean') if 'sales' in df_c3.columns else ('sub_category', 'count')
                    )
                    .reset_index()
                    .rename(columns={'sub_category': 'Sub-Kategori'})
                    .sort_values('Jumlah', ascending=True)
                )

                selected_sub = st.session_state.get('cf_sub_category')
                sub_data['_opacity'] = sub_data['Sub-Kategori'].apply(
                    lambda x: 1.0 if (selected_sub is None or x == selected_sub) else 0.35
                )

                fig_sub = go.Figure()
                for _, row in sub_data.iterrows():
                    fig_sub.add_trace(go.Bar(
                        y=[row['Sub-Kategori']],
                        x=[row['Jumlah']],
                        orientation='h',
                        name=row['Sub-Kategori'],
                        opacity=row['_opacity'],
                        customdata=[[row['Total_Sales'], row['Avg_Sales']]],
                        hovertemplate=(
                            "<b>%{y}</b><br>"
                            "Jumlah: <b>%{x:,}</b><br>"
                            "Total Sales: <b>$%{customdata[0]:,.2f}</b><br>"
                            "Avg Sales: <b>$%{customdata[1]:,.2f}</b>"
                            "<extra></extra>"
                        ),
                    ))

                fig_sub.update_layout(
                    title="Sub-Kategori Produk",
                    showlegend=False,
                    xaxis_title="Jumlah Transaksi",
                    yaxis={'categoryorder': 'total ascending'},
                )

                event_sub = st.plotly_chart(
                    fig_sub, use_container_width=True,
                    on_select="rerun", key="chart_sub_category"
                )
                clicked_sub = get_click_value(event_sub, 'y')
                if clicked_sub:
                    if st.session_state.cf_sub_category == clicked_sub:
                        st.session_state.cf_sub_category = None
                    else:
                        st.session_state.cf_sub_category = clicked_sub
                    st.rerun()

        # --- [CHART 2] Donut Chart: Mode Pengiriman ---
        with col2:
            if 'ship_mode' in df_base.columns:
                df_c5 = apply_crossfilters(df_month, exclude=['ship_mode'])

                ship_data = (
                    df_c5.groupby('ship_mode')
                    .agg(
                        Jumlah=('ship_mode', 'count'),
                        Total_Sales=('sales', 'sum') if 'sales' in df_c5.columns else ('ship_mode', 'count'),
                    )
                    .reset_index()
                    .rename(columns={'ship_mode': 'Mode Pengiriman'})
                )

                selected_ship = st.session_state.get('cf_ship_mode')
                pull_ship = [
                    0.1 if (selected_ship and row['Mode Pengiriman'] == selected_ship) else 0
                    for _, row in ship_data.iterrows()
                ]

                fig_donut = go.Figure(go.Pie(
                    labels=ship_data['Mode Pengiriman'],
                    values=ship_data['Jumlah'],
                    hole=0.45,
                    pull=pull_ship,
                    customdata=ship_data['Total_Sales'],
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Jumlah Pengiriman: <b>%{value:,}</b><br>"
                        "Persentase: <b>%{percent}</b><br>"
                        "Total Sales: <b>$%{customdata:,.2f}</b>"
                        "<extra></extra>"
                    ),
                    textinfo='label+percent',
                ))
                fig_donut.update_layout(title="Opsi Pengiriman")

                event_donut = st.plotly_chart(
                    fig_donut, use_container_width=True,
                    on_select="rerun", key="chart_ship_mode"
                )
                clicked_ship = get_click_value(event_donut, 'label')
                if clicked_ship:
                    if st.session_state.cf_ship_mode == clicked_ship:
                        st.session_state.cf_ship_mode = None
                    else:
                        st.session_state.cf_ship_mode = clicked_ship
                    st.rerun()

        # =====================================================
        # BARIS 3: TREN HARIAN
        # =====================================================
        # --- BARIS KEDUA (Full Width): Line Chart Tren Penjualan Harian ---
        # Dengan menaruhnya di luar blok "with col:", grafik otomatis mengambil seluruh lebar halaman Streamlit
        if 'order_date' in df_base.columns and 'sales' in df_base.columns:
            df_c4 = apply_crossfilters(df_month)  # terapkan semua cross-filter

            daily_sales = df_c4.groupby('order_date').agg(
                sales=('sales', 'sum'),
                transaksi=('sales', 'count'),
            ).reset_index()

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=daily_sales['order_date'],
                y=daily_sales['sales'],
                mode='lines+markers',
                line=dict(color='#2ca02c', width=2),
                marker=dict(size=5),
                customdata=daily_sales['transaksi'],
                hovertemplate=(
                    "<b>%{x|%d %b %Y}</b><br>"
                    "Total Sales: <b>$%{y:,.2f}</b><br>"
                    "Jumlah Transaksi: <b>%{customdata:,}</b>"
                    "<extra></extra>"
                ),
                name='Sales Harian',
            ))

            # Tambahkan moving average 7 hari sebagai referensi
            if len(daily_sales) >= 7:
                daily_sales['ma7'] = daily_sales['sales'].rolling(7).mean()
                fig_line.add_trace(go.Scatter(
                    x=daily_sales['order_date'],
                    y=daily_sales['ma7'],
                    mode='lines',
                    line=dict(color='orange', width=1.5, dash='dash'),
                    hovertemplate="MA-7: <b>$%{y:,.2f}</b><extra></extra>",
                    name='Moving Avg (7 hari)',
                ))

            fig_line.update_layout(
                title="Tren Penjualan Harian",
                xaxis_title="Tanggal",
                yaxis_title="Total Sales ($)",
                hovermode='x unified',
                legend=dict(orientation='h', y=-0.2),
            )
            st.plotly_chart(fig_line, use_container_width=True, key="chart_tren")

        # =====================================================
        # BARIS 4: CHOROPLETH MAP (GEOGRAFIS)
        # =====================================================
        st.divider()
        st.write("#### 🗺️ Analisis Geografis")
        st.caption("Klik sebuah State untuk memfilter semua grafik berdasarkan wilayah tersebut.")

        if 'state' in df_base.columns and 'sales' in df_base.columns:
            df_c6 = apply_crossfilters(df_month, exclude=['state'])

            us_state_to_abbrev = {
                "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
                "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
                "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
                "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
                "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
                "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
                "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
                "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
                "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
                "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
                "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
                "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
                "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC"
            }

            state_agg = (
                df_c6.groupby('state')
                .agg(
                    sales=('sales', 'sum'),
                    transaksi=('sales', 'count'),
                    avg_sales=('sales', 'mean'),
                )
                .reset_index()
            )
            state_agg['state_code'] = state_agg['state'].map(us_state_to_abbrev)
            state_agg = state_agg.dropna(subset=['state_code'])

            selected_state = st.session_state.get('cf_state')

            fig_map = go.Figure(go.Choropleth(
                locations=state_agg['state_code'],
                locationmode="USA-states",
                z=state_agg['sales'],
                text=state_agg['state'],
                customdata=state_agg[['transaksi', 'avg_sales']].values,
                colorscale="Blues",
                colorbar_title="Total Sales ($)",
                # Highlight state yang dipilih
                marker_line_width=[
                    3 if (selected_state and row['state'] == selected_state) else 0.5
                    for _, row in state_agg.iterrows()
                ],
                marker_line_color=[
                    'red' if (selected_state and row['state'] == selected_state) else 'white'
                    for _, row in state_agg.iterrows()
                ],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Total Sales: <b>$%{z:,.2f}</b><br>"
                    "Jumlah Transaksi: <b>%{customdata[0]:,}</b><br>"
                    "Avg Sales/Transaksi: <b>$%{customdata[1]:,.2f}</b>"
                    "<extra></extra>"
                ),
            ))
            fig_map.update_layout(
                title="Peta Persebaran Total Revenue per State (Klik State untuk Cross-filter)",
                geo_scope='usa',
                margin=dict(l=0, r=0, t=40, b=0),
            )

            event_map = st.plotly_chart(
                fig_map, use_container_width=True,
                on_select="rerun", key="chart_map"
            )

            # Tangkap klik dari choropleth — klik ada di 'location' atau 'text'
            if event_map and event_map.get('selection') and event_map['selection'].get('points'):
                pt = event_map['selection']['points'][0]
                clicked_state_code = pt.get('location')
                # Konversi kode balik ke nama negara bagian
                abbrev_to_state = {v: k for k, v in us_state_to_abbrev.items()}
                clicked_state = abbrev_to_state.get(clicked_state_code)
                if clicked_state:
                    if st.session_state.cf_state == clicked_state:
                        st.session_state.cf_state = None
                    else:
                        st.session_state.cf_state = clicked_state
                    st.rerun()

        # =====================================================
        # BARIS 5: SCATTER PLOT (Sales vs Profit)
        # =====================================================
        if 'profit' in df_base.columns and 'sales' in df_base.columns:
            st.divider()
            st.write("#### 💹 Analisis Sales vs Profit")

            df_scatter = apply_crossfilters(df_month)

            color_col = 'category' if 'category' in df_scatter.columns else None
            size_col  = 'quantity' if 'quantity' in df_scatter.columns else None

            hover_data_map = {}
            for col in ['sub_category', 'segment', 'ship_mode', 'state', 'product_name']:
                if col in df_scatter.columns:
                    hover_data_map[col] = True

            fig_scatter = px.scatter(
                df_scatter,
                x='sales', y='profit',
                color=color_col,
                size=size_col,
                hover_data=hover_data_map,
                title="Distribusi Sales vs Profit per Transaksi",
                labels={'sales': 'Sales ($)', 'profit': 'Profit ($)'},
                opacity=0.65,
            )
            fig_scatter.update_traces(
                hovertemplate=(
                    "<b>Sales:</b> $%{x:,.2f}<br>"
                    "<b>Profit:</b> $%{y:,.2f}<br>"
                    "<extra></extra>"
                )
            )
            # Garis breakeven (profit = 0)
            fig_scatter.add_hline(y=0, line_dash='dash', line_color='red',
                                  annotation_text="Breakeven", annotation_position="bottom right")

            st.plotly_chart(fig_scatter, use_container_width=True, key="chart_scatter")

        # =====================================================
        # PREDIKSI MACHINE LEARNING
        # =====================================================
        st.divider()
        st.subheader("🤖 Analisis Prediktif (Machine Learning)")

        df_for_ml = pd.read_sql("SELECT order_month, sales FROM superstore_retail", con=engine)
        fig_prediksi = run_revenue_prediction(df_for_ml)
        st.plotly_chart(fig_prediksi, use_container_width=True, key="chart_ml")

        # =====================================================
        # DATA TABLE INTERAKTIF (opsional, bisa di-expand)
        # =====================================================
        st.divider()
        with st.expander("📋 Lihat Data Tabel (sesuai filter aktif)", expanded=False):
            df_table = apply_crossfilters(df_month)
            st.dataframe(
                df_table,
                use_container_width=True,
                height=350,
            )
            st.caption(f"Menampilkan {len(df_table):,} dari {len(df_raw):,} baris data.")

    except Exception as e:
        st.error(f"Gagal memuat data dari database. Error: {e}")
        st.exception(e)  # detail traceback untuk debugging