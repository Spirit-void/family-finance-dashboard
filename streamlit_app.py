import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import plotly.express as px
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="Dashboard Keuangan Keluarga Interaktif",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Stylish Headers with Custom CSS ---
st.markdown("""
    <style>
        .main-header {
            font-size: 2.5em;
            font-weight: bold;
            color: #4A90E2; /* Bright Blue */
            padding-bottom: 10px;
            border-bottom: 4px solid #4A90E2;
            text-align: center;
            margin-bottom: 20px;
        }
        .subheader {
            font-size: 1.2em;
            color: #666;
            text-align: center;
            margin-bottom: 30px;
        }
        .metric-box {
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); /* More prominent shadow */
            text-align: center;
            margin-bottom: 20px;
            transition: transform 0.3s;
        }
        .metric-box:hover {
            transform: translateY(-5px);
        }
        .metric-title {
            font-weight: 500;
            font-size: 0.9em;
            color: #4b4b4b;
        }
        .metric-value {
            font-size: 2.0em;
            font-weight: bold;
            margin-top: 5px;
        }
    </style>
    <div class="main-header">🏠 Dashboard Keuangan Keluarga</div>
    <div class="subheader">Catatan Keuangan & Pertumbuhan Aset Bersama</div>
""", unsafe_allow_html=True)


# --- Google Sheets Connection (Secure with st.secrets) ---

# Helper function for currency formatting (Indonesian format)
def format_rp(amount):
    """Formats number to Indonesian Rupiah currency string."""
    try:
        return f"Rp {amount:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "Rp 0"

@st.cache_resource(ttl=3600)
def get_google_sheet_client():
    """Initializes and returns the Google Sheet client."""
    try:
        # Load credentials securely from Streamlit Secrets
        creds_json = st.secrets["google_sheets"]["service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ])
        client = gspread.authorize(creds)
        
        # Open the specific spreadsheet
        sheet = client.open(st.secrets["google_sheets"]["spreadsheet_name"]).sheet1
        return sheet
    except Exception as e:
        st.error(f"Koneksi Google Sheets Gagal. Pastikan file 'secrets.toml' dan izin sheet sudah benar. Error: {e}")
        st.stop()
        return None

# --- Data Loading and Processing ---

@st.cache_data(ttl=60)
def load_data(sheet):
    """Fetches data from Google Sheet and processes it."""
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Gagal mengambil data dari Sheet. Pastikan header baris pertama sudah benar. Error: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    # CRITICAL: Verify and standardize column names
    required_cols = ['Tanggal', 'Tipe Transaksi', 'Keterangan', 'Jumlah (Rp)', 'Gram Emas']
    
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Kolom '{col}' tidak ditemukan di Google Sheet. Mohon periksa kembali header kolom (baris 1).")
            return pd.DataFrame()

    # Data Type Conversion and Cleaning
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df['Jumlah (Rp)'] = pd.to_numeric(df['Jumlah (Rp)'], errors='coerce').fillna(0)
    df['Gram Emas'] = pd.to_numeric(df['Gram Emas'], errors='coerce').fillna(0)
    
    # Create calculated columns for easy metric extraction
    df['Pemasukan'] = df.apply(lambda row: row['Jumlah (Rp)'] if row['Tipe Transaksi'] == 'Pemasukan' else 0, axis=1)
    df['Pengeluaran'] = df.apply(lambda row: row['Jumlah (Rp)'] if row['Tipe Transaksi'] == 'Pengeluaran Harian' else 0, axis=1)
    df['Investasi Saham'] = df.apply(lambda row: row['Jumlah (Rp)'] if row['Tipe Transaksi'] == 'Tabungan Saham' else 0, axis=1)
    df['Beli Emas (Rp)'] = df.apply(lambda row: row['Jumlah (Rp)'] if row['Tipe Transaksi'] == 'Beli Emas' else 0, axis=1)
    
    return df

sheet = get_google_sheet_client()
df = load_data(sheet)


# --- Core Metrics Calculation ---
if not df.empty:
    total_pemasukan = df['Pemasukan'].sum()
    total_pengeluaran = df['Pengeluaran'].sum()
    total_tabungan_saham = df['Investasi Saham'].sum()
    total_gram_emas = df['Gram Emas'].sum()
    
    saldo_cashflow = total_pemasukan - total_pengeluaran
    
    total_kekayaan = saldo_cashflow + total_tabungan_saham + (total_gram_emas * 900000) # Assuming Rp900k/gram for quick estimate

    # --- Display Metrics (Key Performance Indicators) ---
    st.subheader("📊 Ringkasan Kekayaan dan Saldo")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div class='metric-box' style='background-color: #e6f7ff; border-left: 5px solid #4A90E2;'>
                <div class='metric-title'>Total Kekayaan (Est.)</div>
                <div class='metric-value' style='color: #4A90E2;'>{format_rp(total_kekayaan)}</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class='metric-box' style='background-color: #e6ffe6; border-left: 5px solid #2ECC71;'>
                <div class='metric-title'>Saldo Bersih (Pemasukan - Pengeluaran)</div>
                <div class='metric-value' style='color: #2ECC71;'>{format_rp(saldo_cashflow)}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
            <div class='metric-box' style='background-color: #fffae6; border-left: 5px solid #F1C40F;'>
                <div class='metric-title'>Total Tabungan Saham</div>
                <div class='metric-value' style='color: #F1C40F;'>{format_rp(total_tabungan_saham)}</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class='metric-box' style='background-color: #ffe6e6; border-left: 5px solid #E74C3C;'>
                <div class='metric-title'>Total Tabungan Emas (Gram)</div>
                <div class='metric-value' style='color: #E74C3C;'>{total_gram_emas:,.2f} Gram</div>
            </div>
        """, unsafe_allow_html=True)


# --- Form Input Data Baru ---
st.markdown("---")
st.subheader("✍️ Catat Transaksi Keuangan")
st.caption("Gunakan bagian ini untuk memasukkan data Pemasukan, Pengeluaran, Tabungan Saham, atau pembelian Emas.")

with st.form("input_form"):
    cols_input = st.columns([1, 1, 1.5])
    tanggal = cols_input[0].date_input("Tanggal Transaksi", value=datetime.today())
    
    transaction_type = cols_input[1].selectbox(
        "Pilih Tipe Transaksi", 
        ["Pemasukan", "Pengeluaran Harian", "Tabungan Saham", "Beli Emas"]
    )
    
    jumlah_rp = cols_input[2].number_input("Jumlah Uang (Rp)", min_value=0, value=0, step=1000)
    
    gram_emas = 0
    if transaction_type == "Beli Emas":
        gram_emas = st.number_input("Jumlah Gram Emas yang Dibeli", min_value=0.00, value=0.00, step=0.01)

    keterangan = st.text_input("Keterangan (Contoh: Gaji Istri, Bayar Listrik, Beli Saham BBCA, Beli Emas 1gr)")
    
    submit = st.form_submit_button("Simpan Transaksi ke Google Sheet")

if submit:
    if jumlah_rp == 0 and gram_emas == 0:
        st.warning("Anda harus memasukkan Jumlah Uang (Rp) atau Gram Emas.")
    else:
        try:
            # Data to be appended to Google Sheets
            row_data = [
                tanggal.strftime("%Y-%m-%d"),
                transaction_type,
                keterangan,
                jumlah_rp,
                gram_emas
            ]
            
            sheet.append_row(row_data)
            
            st.success(f"✅ Transaksi '{transaction_type}' sebesar {format_rp(jumlah_rp)} berhasil disimpan!")
            # Clear cache and rerun to update dashboard immediately
            load_data.clear()
            st.experimental_rerun()
            
        except Exception as e:
            st.error(f"Terjadi kesalahan saat menyimpan data: {e}")

# --- Data Visualization and History ---
if not df.empty:
    st.markdown("---")
    tab1, tab2 = st.tabs(["Visualisasi & Analisis", "Histori Transaksi Detail"])

    with tab1:
        st.subheader("📈 Analisis Pergerakan Keuangan")
        
        # 1. Pie Chart: Uang Mengalir Kemana? (Pengeluaran vs Tabungan)
        
        # Group and prepare data for the Pie Chart
        flow_df = df.groupby('Tipe Transaksi')['Jumlah (Rp)'].sum().reset_index()
        flow_df = flow_df[flow_df['Tipe Transaksi'].isin(['Pengeluaran Harian', 'Tabungan Saham', 'Beli Emas'])]
        
        if not flow_df.empty and flow_df['Jumlah (Rp)'].sum() > 0:
            fig1 = px.pie(
                flow_df,
                values='Jumlah (Rp)',
                names='Tipe Transaksi',
                title='Alokasi Uang (Pengeluaran vs Tabungan)',
                color_discrete_sequence=px.colors.sequential.Agsunset,
                hole=.3 # Donut chart style
            )
            fig1.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Belum ada Pengeluaran atau Tabungan yang tercatat untuk dianalisis.")

        # 2. Line Chart: Tren Saldo Bersih Kumulatif
        try:
            df_trend = df.sort_values('Tanggal')
            df_trend['Cashflow Harian'] = df_trend['Pemasukan'] - df_trend['Pengeluaran']
            df_trend['Kekayaan Kumulatif'] = df_trend['Cashflow Harian'].cumsum()

            fig2 = px.line(
                df_trend.dropna(subset=['Tanggal']), # Drop rows where Tanggal is NaT
                x='Tanggal', 
                y='Kekayaan Kumulatif', 
                title='Tren Saldo Bersih (Cashflow) dari Waktu ke Waktu',
                markers=True,
                line_shape='spline' # Smoother line
            )
            fig2.update_traces(line_color='#008080')
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.info("Tidak cukup data (atau format tanggal bermasalah) untuk membuat grafik tren kumulatif.")


    with tab2:
        st.subheader("📃 Riwayat Transaksi Lengkap")
        # Displaying the clean data frame
        display_df = df.sort_values('Tanggal', ascending=False)[['Tanggal', 'Tipe Transaksi', 'Keterangan', 'Jumlah (Rp)', 'Gram Emas']]
        display_df['Jumlah (Rp)'] = display_df['Jumlah (Rp)'].apply(format_rp)
        display_df['Gram Emas'] = display_df['Gram Emas'].apply(lambda x: f"{x:,.2f}" if x > 0 else "")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
            
else:
    st.markdown("---")
    st.warning("Belum ada data yang berhasil dimuat dari Google Sheets. Silakan masukkan transaksi pertama Anda di atas, atau cek kembali koneksi Google Sheets.")
