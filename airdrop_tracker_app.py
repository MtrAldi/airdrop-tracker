import streamlit as st
import pandas as pd
import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title="Airdrop Tracker Testnet",
    page_icon="🪂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tema terminal: warna, font, dan badge ada di sini; warna dasar dan font
# bawaan Streamlit ada di .streamlit/config.toml.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

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
    --mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
}
html, body, [data-testid="stAppViewContainer"] { background-color: var(--bg); color: var(--fg); }
[data-testid="stSidebar"] { background-color: var(--card); border-right: 1px solid var(--border); }
[data-testid="stSidebar"] h1 { font-size: 1.6rem; }
.stButton>button { background-color: var(--accent); color: #0d1117; border: none; font-weight: 600; border-radius: 4px; }
.stButton>button:hover { background-color: var(--accent-dim); }
.stButton>button:focus { box-shadow: 0 0 0 2px var(--accent); }
.stTextInput>div>div>input, .stTextArea>div>textarea { background-color: var(--card); border: 1px solid var(--border); color: var(--fg); }
.stDateInput>div>div>input { background-color: var(--card); border: 1px solid var(--border); color: var(--fg); }
[data-testid="stMetric"] { background-color: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
[data-testid="stMetricLabel"] { color: #8b949e !important; }
[data-testid="stMetricValue"] { color: var(--accent) !important; font-family: var(--mono); }
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { background-color: var(--card); border: 1px solid var(--border); color: var(--fg); border-radius: 4px 4px 0 0; padding: 0.5rem 1rem; }
.stTabs [aria-selected="true"] { background-color: var(--accent); color: #0d1117; border-color: var(--accent); }
h1, h2, h3, h4 { color: var(--accent) !important; font-family: var(--mono) !important; }
hr { border-color: var(--border); }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "airdrop_tracker.db"
SEED_FILE = BASE_DIR / "initial_data.json"

STATUSES = [
    "Confirmed",
    "Potential / Speculative",
    "Testnet Active",
    "Active / Farming",
    "Snapshot Taken",
    "Verification Open",
    "Claimable",
    "Distributed / Done",
]

# Substring yang dicocokkan ke kolom status untuk filter sidebar.
STATUS_FILTERS = ["Confirmed", "Potential", "Testnet", "Active", "Done", "Distributed"]

STATUS_PALETTE = {
    "confirmed": ("#3fb950", "#0d1117"),
    "potential": ("#d29922", "#0d1117"),
    "testnet": ("#58a6ff", "#0d1117"),
    "done": ("#f85149", "#ffffff"),
    "active": ("#2ea043", "#ffffff"),
}

STATIC_COLUMNS = ["project_name", "token_name", "status", "url",
                  "start_date", "end_date", "requirements", "notes"]


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
        c.execute("SELECT COUNT(*) FROM airdrop_tracker")
        if c.fetchone()[0] == 0 and SEED_FILE.exists():
            seed_from_json(conn)
    except Exception as e:
        st.error(f"Error initializing database: {e}")


def seed_from_json(conn):
    try:
        with open(SEED_FILE, 'r') as f:
            data = json.load(f)
        c = conn.cursor()
        for row in data:
            row_data = {k: v for k, v in row.items() if k in STATIC_COLUMNS and pd.notna(v)}
            if row_data:
                cols = list(row_data.keys())
                placeholders = ', '.join(['?'] * len(cols))
                c.execute(f'INSERT INTO airdrop_tracker ({", ".join(cols)}) VALUES ({placeholders})',
                          list(row_data.values()))
        conn.commit()
        st.success(f"Database diisi otomatis dari {SEED_FILE.name} ({len(data)} records)")
    except Exception as e:
        st.warning(f"Gagal seeding dari JSON: {e}")


# Filter dan pencarian sengaja dijalankan di pandas, bukan disusun jadi SQL,
# supaya input sidebar tidak pernah masuk ke kueri.
@st.cache_data
def load_data():
    conn = get_connection()
    df = pd.read_sql_query(
        'SELECT * FROM airdrop_tracker ORDER BY start_date NULLS LAST, id DESC', conn)
    for col in ['start_date', 'end_date', 'created_at', 'updated_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
    return df


def insert_data(data):
    conn = get_connection()
    c = conn.cursor()
    cols = list(data.keys())
    placeholders = ', '.join(['?'] * len(cols))
    c.execute(f'INSERT INTO airdrop_tracker ({", ".join(cols)}) VALUES ({placeholders})',
              list(data.values()))
    conn.commit()
    return c.lastrowid


def update_data(airdrop_id, data):
    conn = get_connection()
    c = conn.cursor()
    vals = list(data.values()) + [datetime.now().isoformat(), airdrop_id]
    cols = [f'{k} = ?' for k in data] + ['updated_at = ?']
    c.execute(f'UPDATE airdrop_tracker SET {", ".join(cols)} WHERE id = ?', vals)
    conn.commit()


def delete_data(airdrop_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM airdrop_tracker WHERE id = ?', (airdrop_id,))
    conn.commit()


def status_palette(status):
    lowered = status.lower()
    if 'confirm' in lowered:
        return STATUS_PALETTE["confirmed"]
    if 'potential' in lowered or 'spec' in lowered or 'rumor' in lowered:
        return STATUS_PALETTE["potential"]
    if 'testnet' in lowered:
        return STATUS_PALETTE["testnet"]
    if 'done' in lowered or 'distribut' in lowered or 'claim' in lowered:
        return STATUS_PALETTE["done"]
    if 'active' in lowered or 'live' in lowered or 'farm' in lowered:
        return STATUS_PALETTE["active"]
    return ("#30363d", "#c9d1d9")


# st.dataframe tidak merender HTML, jadi warna badge datang dari Styler.
def status_cell_style(value):
    bg, fg = status_palette(value)
    return f"background-color: {bg}; color: {fg}; font-weight: 600"


URL_RE = re.compile(r'https?://\S+')
TOKEN_RE = re.compile(r'\$[A-Z][A-Z0-9]{1,9}\b')

# Kata yang sering jadi kalimat pembuka tweet, bukan nama project.
NAME_STOPWORDS = {
    "new", "airdrop", "airdrops", "official", "confirmed", "the", "this",
    "that", "get", "join", "now", "yes", "free", "hunt", "we", "i", "it", "its", "is",
    "are", "a", "an", "our", "my", "testnet", "mainnet", "token", "layer", "season",
    "phase", "round", "update", "drop", "task", "tasks", "farm", "farming", "snapshot",
    "claim", "claimable", "distribution", "source", "alpha", "insider", "gm", "wagmi",
}


def guess_project_name(text, token):
    body = URL_RE.sub(" ", text)
    targeted = re.search(
        r'\bairdrops?\s+(?:for|from|of)\s+([A-Za-z][A-Za-z0-9]{1,20})', body, re.IGNORECASE)
    if targeted:
        return targeted.group(1)
    for word in re.findall(r'\b[A-Z][A-Za-z0-9]{1,20}\b', body):
        if word != token and word.lower() not in NAME_STOPWORDS:
            return word
    return ""


def parse_tweet_text(text):
    res = {
        'project_name': '',
        'token_name': '',
        'status': 'Potential / Speculative',
        'url': '',
        'requirements': text,
        'notes': ''
    }

    token = TOKEN_RE.search(text)
    if token:
        res['token_name'] = token.group(0)

    url = URL_RE.search(text)
    if url:
        res['url'] = url.group(0)

    res['project_name'] = guess_project_name(text, res['token_name'])

    text_lower = text.lower()
    if 'confirm' in text_lower or 'official' in text_lower:
        res['status'] = 'Confirmed'
    elif 'testnet' in text_lower:
        res['status'] = 'Testnet Active'
    elif 'farm' in text_lower or 'live' in text_lower:
        res['status'] = 'Active / Farming'

    return res


def flash(message, kind="success"):
    st.session_state["flash"] = (kind, message)


def render_flash():
    # st.rerun() menghapus semua elemen yang sudah dirender, jadi pesan harus
    # disimpan di session_state lalu digambar ulang setelah rerun.
    if "flash" in st.session_state:
        kind, message = st.session_state.pop("flash")
        getattr(st, kind)(message)


def record_form(project_name, token_name, status, url, start_date, end_date, requirements, notes):
    return {
        'project_name': project_name,
        'token_name': token_name or None,
        'status': status,
        'url': url or None,
        'start_date': start_date.isoformat() if start_date else None,
        'end_date': end_date.isoformat() if end_date else None,
        'requirements': requirements or None,
        'notes': notes or None,
    }


init_db()

with st.sidebar:
    st.title("Airdrop Tracker")
    st.caption("Testnet & Mainnet Farming Monitor")
    st.divider()

    menu = st.radio("Navigasi",
                    ["Dashboard", "Tambah Airdrop", "Edit/Hapus", "Parser Tweet", "Import/Export"],
                    label_visibility="collapsed")
    st.divider()

    st.subheader("Filter")
    f_status = st.multiselect("Status", STATUS_FILTERS, default=[])
    f_search = st.text_input("Cari Project / Token / URL")
    f_date_from = st.date_input("Dari Tanggal", value=None, format="YYYY-MM-DD")
    f_date_to = st.date_input("Sampai Tanggal", value=None, format="YYYY-MM-DD")

    st.divider()
    st.caption(f"DB: {DB_PATH.name}")
    if st.button("Refresh Data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

df = load_data()

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

render_flash()

if menu == "Dashboard":
    st.title("Dashboard Airdrop")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tracked", len(df))
    col2.metric("Confirmed", len(df[df['status'].str.contains('confirm', case=False, na=False)]))
    col3.metric("Testnet", len(df[df['status'].str.contains('testnet', case=False, na=False)]))
    col4.metric("Active", len(df[df['status'].str.contains('active|live|farm', case=False, na=False)]))

    st.divider()

    if not df.empty:
        display_df = df.copy()
        display_df['days_left'] = display_df.apply(
            lambda row: (pd.to_datetime(row['end_date']) - pd.Timestamp.now()).days
            if pd.notna(row['end_date']) and row['end_date'] else None, axis=1
        )
        display_df = display_df[['id', 'project_name', 'token_name', 'status',
                                 'start_date', 'end_date', 'days_left', 'url']].rename(columns={
            'id': 'ID',
            'project_name': 'Project',
            'token_name': 'Token',
            'status': 'Status',
            'start_date': 'Mulai',
            'end_date': 'Selesai',
            'days_left': 'Sisa Hari',
            'url': 'Link'
        })

        st.dataframe(
            display_df.style.map(status_cell_style, subset=['Status']),
            width="stretch",
            hide_index=True,
            column_config={
                "Link": st.column_config.LinkColumn("Link", display_text="Buka"),
                "Sisa Hari": st.column_config.NumberColumn("Sisa Hari", format="%d hari"),
            }
        )

        st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'),
                           "airdrop_tracker.csv", "text/csv", width="stretch")
    else:
        st.info("Belum ada data airdrop. Tambahkan di tab 'Tambah Airdrop'.")

elif menu == "Tambah Airdrop":
    st.title("Tambah Airdrop Baru")

    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Nama Project *",
                                         placeholder="Contoh: Variational, Canopy, GIWA")
            token_name = st.text_input("Nama Token", placeholder="Contoh: $USD, $CNPY, $KNX")
            status = st.selectbox("Status *", STATUSES, index=0)
            url = st.text_input("URL Resmi / Dashboard", placeholder="https://...")
        with col2:
            start_date = st.date_input("Tanggal Mulai", value=None, format="YYYY-MM-DD")
            end_date = st.date_input("Tanggal Selesai / Deadline", value=None, format="YYYY-MM-DD")
            requirements = st.text_area(
                "Persyaratan / Tugas",
                placeholder="Contoh: Bridge Sepolia ETH, deploy contract, daily check-in, volume $200...")
            notes = st.text_area("Catatan", placeholder="Catatan tambahan: modal min, chain, "
                                                         "referal code, risiko, dsb.")

        if st.form_submit_button("Simpan", width="stretch", type="primary"):
            if not project_name:
                st.error("Nama Project wajib diisi.")
            else:
                new_id = insert_data(
                    record_form(project_name, token_name, status, url,
                                start_date, end_date, requirements, notes))
                st.cache_data.clear()
                flash(f"Berhasil ditambahkan. ID: {new_id}")
                st.rerun()

elif menu == "Edit/Hapus":
    st.title("Edit / Hapus Airdrop")

    if df.empty:
        st.info("Tidak ada data untuk diedit.")
    else:
        labels = {r['id']: r['project_name'] for _, r in df.iterrows()}
        selected_id = st.selectbox(
            "Pilih Airdrop (ID - Project)",
            options=list(labels),
            format_func=lambda x: f"{x} - {labels[x]}",
            key="edit_selected_id"
        )
        row = df[df['id'] == selected_id].iloc[0]

        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("Nama Project *", value=row['project_name'])
                token_name = st.text_input(
                    "Nama Token", value=row['token_name'] if pd.notna(row['token_name']) else "")
                status = st.selectbox(
                    "Status *", STATUSES,
                    index=STATUSES.index(row['status']) if row['status'] in STATUSES else 0)
                url = st.text_input("URL", value=row['url'] if pd.notna(row['url']) else "")

            with col2:
                start_date_val = pd.to_datetime(row['start_date'], errors='coerce')
                start_date = st.date_input("Tanggal Mulai",
                                           value=start_date_val if pd.notna(start_date_val) else None,
                                           format="YYYY-MM-DD")
                end_date_val = pd.to_datetime(row['end_date'], errors='coerce')
                end_date = st.date_input("Tanggal Selesai",
                                         value=end_date_val if pd.notna(end_date_val) else None,
                                         format="YYYY-MM-DD")
                requirements = st.text_area(
                    "Persyaratan", value=row['requirements'] if pd.notna(row['requirements']) else "")
                notes = st.text_area("Catatan", value=row['notes'] if pd.notna(row['notes']) else "")

            col_save, col_del = st.columns(2)
            with col_save:
                save = st.form_submit_button("Update", width="stretch", type="primary")
            with col_del:
                delete = st.form_submit_button("Hapus", width="stretch", type="secondary")

            if save:
                update_data(selected_id,
                            record_form(project_name, token_name, status, url,
                                        start_date, end_date, requirements, notes))
                st.cache_data.clear()
                flash("Data diperbarui.")
                st.rerun()

            if delete:
                delete_data(selected_id)
                st.cache_data.clear()
                flash(f"Data ID {selected_id} dihapus.", "warning")
                st.rerun()

elif menu == "Parser Tweet":
    st.title("Parser Tweet")
    st.caption("Tempel teks tweet atau thread airdrop untuk di-parse secara otomatis.")

    tweet_text = st.text_area(
        "Tempel Teks Tweet di Sini", height=200,
        placeholder="Contoh: New confirmed airdrop for Asentum $ASE. Join the testnet now: "
                    "https://asentum.xyz ...")

    if st.button("Parse Tweet", width="stretch", type="primary"):
        if not tweet_text:
            st.error("Silakan tempel teks tweet terlebih dahulu.")
        else:
            st.session_state['parsed_data'] = parse_tweet_text(tweet_text)

    if 'parsed_data' in st.session_state:
        st.divider()
        st.subheader("Tinjau Hasil Parsing")

        parsed = st.session_state['parsed_data']

        with st.form("parsed_confirm_form"):
            col1, col2 = st.columns(2)
            with col1:
                p_name = st.text_input("Project Name", value=parsed['project_name'])
                p_token = st.text_input("Token", value=parsed['token_name'])
                p_status = st.selectbox(
                    "Status", STATUSES,
                    index=STATUSES.index(parsed['status'])
                    if parsed['status'] in STATUSES else 1)
                p_url = st.text_input("URL", value=parsed['url'])
            with col2:
                p_start = st.date_input("Start Date", value=None)
                p_end = st.date_input("End Date", value=None)
                p_req = st.text_area("Requirements", value=parsed['requirements'])
                p_notes = st.text_area("Notes", value=parsed['notes'])

            if st.form_submit_button("Konfirmasi & Tambah ke Database",
                                     width="stretch", type="primary"):
                if not p_name:
                    st.error("Project Name wajib diisi.")
                else:
                    insert_data(record_form(p_name, p_token, p_status, p_url,
                                            p_start, p_end, p_req, p_notes))
                    st.cache_data.clear()
                    del st.session_state['parsed_data']
                    flash(f"Project '{p_name}' berhasil ditambahkan.")
                    st.rerun()

elif menu == "Import/Export":
    st.title("Import / Export Data")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Export")
        if st.button("Siapkan File CSV", width="stretch"):
            st.session_state['export_csv'] = load_data().to_csv(index=False).encode('utf-8')
        if 'export_csv' in st.session_state:
            st.download_button("Klik untuk Download", st.session_state['export_csv'],
                               "airdrop_full_export.csv", "text/csv", width="stretch")
        st.caption("Format CSV: id,project_name,token_name,status,url,start_date,end_date,"
                   "requirements,notes,created_at,updated_at")

    with col2:
        st.subheader("Import CSV")
        uploaded = st.file_uploader("Pilih file CSV", type=['csv'])
        if uploaded:
            try:
                imp_df = pd.read_csv(uploaded)
                required = ['project_name', 'status']
                missing = [c for c in required if c not in imp_df.columns]
                if missing:
                    st.error(f"Kolom wajib hilang: {missing}")
                else:
                    st.write("Preview:")
                    st.dataframe(imp_df.head(), width="stretch")
                    if st.button("Konfirmasi Import", width="stretch", type="primary"):
                        count = 0
                        skipped = 0
                        for _, row in imp_df.iterrows():
                            name = row.get('project_name')
                            row_status = row.get('status')
                            # Kolom NOT NULL membuat satu baris rusak menggagalkan
                            # seluruh import, jadi dilewati dan dilaporkan.
                            if pd.isna(name) or not str(name).strip() \
                                    or pd.isna(row_status) or not str(row_status).strip():
                                skipped += 1
                                continue
                            insert_data({
                                'project_name': str(name).strip(),
                                'token_name': None if pd.isna(row.get('token_name'))
                                else str(row.get('token_name')),
                                'status': str(row_status).strip(),
                                'url': None if pd.isna(row.get('url')) else str(row.get('url')),
                                'start_date': None if pd.isna(row.get('start_date'))
                                else str(row.get('start_date')),
                                'end_date': None if pd.isna(row.get('end_date'))
                                else str(row.get('end_date')),
                                'requirements': None if pd.isna(row.get('requirements'))
                                else str(row.get('requirements')),
                                'notes': None if pd.isna(row.get('notes'))
                                else str(row.get('notes')),
                            })
                            count += 1
                        st.cache_data.clear()
                        message = f"{count} record diimport."
                        if skipped:
                            message += f" {skipped} baris dilewati karena project_name atau status kosong."
                        flash(message)
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.caption("Airdrop Testnet Tracker | Streamlit + SQLite | Terminal Green Theme")
