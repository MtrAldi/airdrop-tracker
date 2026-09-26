import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from datetime import date, datetime
from pathlib import Path

# Konfigurasi Halaman
st.set_page_config(
    page_title="Airdrop Tracker Testnet",
    page_icon="🪂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tema "Terminal/CRT Green"
st.markdown("""
<style>
:root {
    --bg: #0d1117;
    --fg: #c9d1d9;
    --accent: #3fb950;
    --accent-dim: #2ea043;
    --card: #161b22;
    --border: #30363d;
    --warn: #d29922;
    --danger: #f85149;
    --info: #58a6ff;
}
html, body, [data-testid="stAppViewContainer"] { background-color: var(--bg); color: var(--fg); }
[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid var(--border); }
.stButton>button { background-color: var(--accent); color: #0d1117; border: none; font-weight: 600; border-radius: 4px; }
.stButton>button:hover { background-color: var(--accent-dim); }
.stButton>button:focus { box-shadow: 0 0 0 2px var(--accent); }
.stTextInput>div>div>input, .stTextArea>div>textarea, .stSelectbox>div>div>div>input { background-color: var(--card); border: 1px solid var(--border); color: var(--fg); }
.stDateInput>div>div>input { background-color: var(--card); border: 1px solid var(--border); color: var(--fg); }
[data-testid="stMetric"] { background-color: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
[data-testid="stMetricLabel"] { color: #8b949e !important; }
[data-testid="stMetricValue"] { color: var(--accent) !important; font-family: 'JetBrains Mono', monospace; }
.stDataFrame { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { background-color: var(--card); border: 1px solid var(--border); color: var(--fg); border-radius: 4px 4px 0 0; padding: 0.5rem 1rem; }
.stTabs [aria-selected="true"] { background-color: var(--accent); color: #0d1117; border-color: var(--accent); }
h1, h2, h3 { color: var(--accent); font-family: 'JetBrains Mono', monospace; }
hr { border-color: var(--border); }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.badge-confirmed { background: var(--accent); color: #0d1117; }
.badge-potential { background: var(--warn); color: #0d1117; }
.badge-testnet { background: var(--info); color: #0d1117; }
.badge-done { background: var(--danger); color: white; }
.badge-active { background: var(--accent-dim); color: white; }
</style>
""", unsafe_allow_html=True)

# --- Database Path ---
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "airdrop_tracker.db"
SEED_FILE = BASE_DIR / "initial_data.json"

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def init_db():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS airdrop_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            token_name TEXT,
            status TEXT NOT NULL,
            url TEXT,
            start_date DATE,
            end_date DATE,
            requirements TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_project_name ON airdrop_tracker(project_name)')
        conn.commit()

        # Auto-seed from initial_data.json if table is empty
        c.execute("SELECT COUNT(*) FROM airdrop_tracker")
        if c.fetchone()[0] == 0 and SEED_FILE.exists():
            seed_from_json(conn)
        # Connection is NOT closed here - managed by @st.cache_resource
        # Closing it would cause "cannot operate on a closed database" on reruns
    except Exception as e:
        st.error(f"Error initializing database: {e}")

def seed_from_json(conn):
    """Isi database dari initial_data.json"""
    try:
        with open(SEED_FILE, 'r') as f:
            data = json.load(f)
        c = conn.cursor()
        for row in data:
            valid_cols = ['project_name', 'token_name', 'status', 'url', 
                          'start_date', 'end_date', 'requirements', 'notes']
            row_data = {k: v for k, v in row.items() if k in valid_cols and pd.notna(v)}
            if row_data:
                cols = list(row_data.keys())
                vals = list(row_data.values())
                placeholders = ', '.join(['?'] * len(cols))
                c.execute(f'INSERT INTO airdrop_tracker ({", ".join(cols)}) VALUES ({placeholders})', vals)
        conn.commit()
        st.success(f"Database diisi otomatis dari {SEED_FILE.name} ({len(data)} records)")
    except Exception as e:
        st.warning(f"Gagal seeding dari JSON: {e}")

def load_data(filters=None):
    conn = get_connection()
    query = 'SELECT * FROM airdrop_tracker ORDER BY start_date NULLS LAST, id DESC'
    params = []
    if filters:
        clauses = []
        for key, val in filters.items():
            if val:
                clauses.append(f'{key} LIKE ?')
                params.append(f'%{val}%')
        if clauses:
            query += ' WHERE ' + ' AND '.join(clauses)
    df = pd.read_sql_query(query, conn, params=params)
    for col in ['start_date', 'end_date', 'created_at', 'updated_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
    return df

def insert_data(data):
    conn = get_connection()
    c = conn.cursor()
    cols = list(data.keys())
    vals = list(data.values())
    placeholders = ', '.join(['?'] * len(cols))
    c.execute(f'INSERT INTO airdrop_tracker ({", ".join(cols)}) VALUES ({placeholders})', vals)
    conn.commit()
    return c.lastrowid

def update_data(airdrop_id, data):
    conn = get_connection()
    c = conn.cursor()
    cols = [f'{k} = ?' for k in data.keys()]
    vals = list(data.values())
    vals.append(datetime.now().isoformat())
    cols.append('updated_at = ?')
    c.execute(f'UPDATE airdrop_tracker SET {", ".join(cols)} WHERE id = ?', vals + [airdrop_id])
    conn.commit()

def delete_data(airdrop_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM airdrop_tracker WHERE id = ?', (airdrop_id,))
    conn.commit()

def get_status_badge(status):
    status_lower = status.lower()
    if 'confirm' in status_lower:
        return f'<span class="badge badge-confirmed">{status}</span>'
    elif 'potential' in status_lower or 'spec' in status_lower or 'rumor' in status_lower:
        return f'<span class="badge badge-potential">{status}</span>'
    elif 'testnet' in status_lower:
        return f'<span class="badge badge-testnet">{status}</span>'
    elif 'done' in status_lower or 'distribut' in status_lower or 'claim' in status_lower:
        return f'<span class="badge badge-done">{status}</span>'
    elif 'active' in status_lower or 'live' in status_lower or 'farm' in status_lower:
        return f'<span class="badge badge-active">{status}</span>'
    return f'<span class="badge" style="background:#30363d;color:#c9d1d9;">{status}</span>'

# Inisialisasi DB
init_db()

# --- Sidebar ---
with st.sidebar:
    st.title("🪂 Airdrop Tracker")
    st.caption("Testnet & Mainnet Farming Monitor")
    st.divider()

    menu = st.radio("Navigasi", ["📊 Dashboard", "➕ Tambah Airdrop", "✏️ Edit/Hapus", "📥 Import/Export"], label_visibility="collapsed")
    st.divider()

    st.subheader("🔍 Filter")
    f_status = st.multiselect("Status", ["Confirmed", "Potential", "Testnet", "Active", "Done", "Distributed"], default=[])
    f_search = st.text_input("Cari Project / Token / URL")
    f_date_from = st.date_input("Dari Tanggal", value=None, format="YYYY-MM-DD")
    f_date_to = st.date_input("Sampai Tanggal", value=None, format="YYYY-MM-DD")

    st.divider()
    st.caption(f"DB: {DB_PATH.name}")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Load Data ---
df = load_data()

# Apply filters
if f_status:
    df = df[df['status'].str.contains('|'.join(f_status), case=False, na=False)]
if f_search:
    mask = df['project_name'].str.contains(f_search, case=False, na=False) | \
           df['token_name'].str.contains(f_search, case=False, na=False) | \
           df['url'].str.contains(f_search, case=False, na=False) | \
           df['requirements'].str.contains(f_search, case=False, na=False) | \
           df['notes'].str.contains(f_search, case=False, na=False)
    df = df[mask]
if f_date_from:
    df = df[pd.to_datetime(df['start_date'], errors='coerce') >= pd.Timestamp(f_date_from)]
if f_date_to:
    df = df[pd.to_datetime(df['end_date'], errors='coerce') <= pd.Timestamp(f_date_to)]

# ==================== DASHBOARD ====================
if menu == "📊 Dashboard":
    st.title("📊 Dashboard Airdrop")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    confirmed = len(df[df['status'].str.contains('confirm', case=False, na=False)])
    testnet = len(df[df['status'].str.contains('testnet', case=False, na=False)])
    active = len(df[df['status'].str.contains('active|live|farm', case=False, na=False)])

    col1.metric("Total Tracked", total)
    col2.metric("✅ Confirmed", confirmed)
    col3.metric("🧪 Testnet", testnet)
    col4.metric("🔥 Active", active)

    st.divider()

    # Tabel dengan badge status
    if not df.empty:
        display_df = df.copy()
        display_df['status_badge'] = display_df['status'].apply(get_status_badge)
        display_df['days_left'] = display_df.apply(
            lambda row: (pd.to_datetime(row['end_date']) - pd.Timestamp.now()).days
            if pd.notna(row['end_date']) and row['end_date'] else None, axis=1
        )

        # Kolom yang ditampilkan
        show_cols = ['id', 'project_name', 'token_name', 'status_badge', 'start_date', 'end_date', 'days_left', 'url']
        display_df = display_df[show_cols].rename(columns={
            'id': 'ID',
            'project_name': 'Project',
            'token_name': 'Token',
            'status_badge': 'Status',
            'start_date': 'Mulai',
            'end_date': 'Selesai',
            'days_left': 'Sisa Hari',
            'url': 'Link'
        })

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Link": st.column_config.LinkColumn("Link", display_text="🔗 Buka"),
                "Sisa Hari": st.column_config.NumberColumn("Sisa Hari", format="%d hari"),
            }
        )

        # Download CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "airdrop_tracker.csv", "text/csv", use_container_width=True)
    else:
        st.info("Belum ada data airdrop. Tambahkan di tab 'Tambah Airdrop'.")

# ==================== TAMBAH AIRDROP ====================
elif menu == "➕ Tambah Airdrop":
    st.title("➕ Tambah Airdrop Baru")

    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Nama Project *", placeholder="Contoh: Variational, Canopy, GIWA")
            token_name = st.text_input("Nama Token", placeholder="Contoh: $USD, $CNPY, $KNX")
            status = st.selectbox("Status *", [
                "Confirmed",
                "Potential / Speculative",
                "Testnet Active",
                "Active / Farming",
                "Snapshot Taken",
                "Verification Open",
                "Claimable",
                "Distributed / Done"
            ], index=0)
            url = st.text_input("URL Resmi / Dashboard", placeholder="https://...")

        with col2:
            start_date = st.date_input("Tanggal Mulai", value=None, format="YYYY-MM-DD")
            end_date = st.date_input("Tanggal Selesai / Deadline", value=None, format="YYYY-MM-DD")
            requirements = st.text_area("Persyaratan / Tugas", placeholder="Contoh: Bridge Sepolia ETH, deploy contract, daily check-in, volume $200...")
            notes = st.text_area("Catatan", placeholder="Catatan tambahan: modal min, chain, referal code, risiko, dsb.")

        submitted = st.form_submit_button("💾 Simpan", use_container_width=True, type="primary")
        if submitted:
            if not project_name:
                st.error("Nama Project wajib diisi.")
            else:
                data = {
                    'project_name': project_name,
                    'token_name': token_name or None,
                    'status': status,
                    'url': url or None,
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None,
                    'requirements': requirements or None,
                    'notes': notes or None,
                }
                new_id = insert_data(data)
                st.success(f"✅ Berhasil ditambahkan! ID: {new_id}")
                st.cache_data.clear()

# ==================== EDIT / HAPUS ====================
elif menu == "✏️ Edit/Hapus":
    st.title("✏️ Edit / Hapus Airdrop")

    if df.empty:
        st.info("Tidak ada data untuk diedit.")
    else:
        # Pilih ID
        selected_id = st.selectbox(
            "Pilih Airdrop (ID - Project)",
            options=df['id'].tolist(),
            format_func=lambda x: f"{x} - {df[df['id']==x]['project_name'].values[0]}"
        )

        row = df[df['id'] == selected_id].iloc[0]

        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("Nama Project *", value=row['project_name'])
                token_name = st.text_input("Nama Token", value=row['token_name'] if pd.notna(row['token_name']) else "")
                status_options = [
                    "Confirmed",
                    "Potential / Speculative",
                    "Testnet Active",
                    "Active / Farming",
                    "Snapshot Taken",
                    "Verification Open",
                    "Claimable",
                    "Distributed / Done"
                ]
                current_status = row['status']
                status_idx = status_options.index(current_status) if current_status in status_options else 0
                status = st.selectbox("Status *", status_options, index=status_idx)
                url = st.text_input("URL", value=row['url'] if pd.notna(row['url']) else "")

            with col2:
                start_date_val = pd.to_datetime(row['start_date'], errors='coerce')
                start_date = st.date_input("Tanggal Mulai", value=start_date_val if pd.notna(start_date_val) else None, format="YYYY-MM-DD")
                end_date_val = pd.to_datetime(row['end_date'], errors='coerce')
                end_date = st.date_input("Tanggal Selesai", value=end_date_val if pd.notna(end_date_val) else None, format="YYYY-MM-DD")
                requirements = st.text_area("Persyaratan", value=row['requirements'] if pd.notna(row['requirements']) else "")
                notes = st.text_area("Catatan", value=row['notes'] if pd.notna(row['notes']) else "")

            col_save, col_del = st.columns(2)
            with col_save:
                save = st.form_submit_button("💾 Update", use_container_width=True, type="primary")
            with col_del:
                delete = st.form_submit_button("🗑️ Hapus", use_container_width=True, type="secondary")

            if save:
                updates = {
                    'project_name': project_name,
                    'token_name': token_name or None,
                    'status': status,
                    'url': url or None,
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None,
                    'requirements': requirements or None,
                    'notes': notes or None,
                }
                update_data(selected_id, updates)
                st.success("✅ Data diperbarui!")
                st.cache_data.clear()
                st.rerun()

            if delete:
                delete_data(selected_id)
                st.warning("🗑️ Data dihapus.")
                st.cache_data.clear()
                st.rerun()

# ==================== IMPORT / EXPORT ====================
elif menu == "📥 Import/Export":
    st.title("📥 Import / Export Data")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📤 Export")
        if st.button("Download CSV Lengkap", use_container_width=True):
            full_df = load_data()
            csv = full_df.to_csv(index=False).encode('utf-8')
            st.download_button("Klik untuk Download", csv, "airdrop_full_export.csv", "text/csv", use_container_width=True)

        st.caption("Format CSV: id,project_name,token_name,status,url,start_date,end_date,requirements,notes,created_at,updated_at")

    with col2:
        st.subheader("📥 Import CSV")
        uploaded = st.file_uploader("Pilih file CSV", type=['csv'])
        if uploaded:
            try:
                imp_df = pd.read_csv(uploaded)
                # Validasi kolom minimal
                required = ['project_name', 'status']
                if all(c in imp_df.columns for c in required):
                    st.write("Preview:")
                    st.dataframe(imp_df.head(), use_container_width=True)
                    if st.button("Konfirmasi Import", use_container_width=True, type="primary"):
                        conn = get_connection()
                        c = conn.cursor()
                        count = 0
                        for _, row in imp_df.iterrows():
                            data = {
                                'project_name': row.get('project_name'),
                                'token_name': row.get('token_name') if pd.notna(row.get('token_name')) else None,
                                'status': row.get('status'),
                                'url': row.get('url') if pd.notna(row.get('url')) else None,
                                'start_date': row.get('start_date') if pd.notna(row.get('start_date')) else None,
                                'end_date': row.get('end_date') if pd.notna(row.get('end_date')) else None,
                                'requirements': row.get('requirements') if pd.notna(row.get('requirements')) else None,
                                'notes': row.get('notes') if pd.notna(row.get('notes')) else None,
                            }
                            cols = list(data.keys())
                            vals = list(data.values())
                            placeholders = ', '.join(['?'] * len(cols))
                            c.execute(f'INSERT INTO airdrop_tracker ({", ".join(cols)}) VALUES ({placeholders})', vals)
                            count += 1
                        conn.commit()
                        st.success(f"✅ {count} record diimport.")
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.error(f"Kolom wajib hilang: {required}")
            except Exception as e:
                st.error(f"Error: {e}")

# Footer
st.divider()
st.caption("🪂 Airdrop Testnet Tracker • Built with Streamlit + SQLite • Terminal Green Theme")