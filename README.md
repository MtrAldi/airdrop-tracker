# 🪂 Airdrop Tracker Testnet

Web app untuk melacak & memantau airdrop crypto (testnet & mainnet) yang sedang difarming. Dibangun dengan Streamlit + SQLite dengan tema **Terminal/CRT Green**.

## ✨ Fitur

- **📊 Dashboard** — ringkasan metrik (total tracked, confirmed, testnet, active) + tabel dengan badge status & countdown sisa hari
- **➕ Tambah Airdrop** — form input: nama project, token, status, URL, tanggal mulai/selesai, persyaratan, catatan
- **✏️ Edit / Hapus** — ubah status atau hapus entry yang sudah selesai
- **📥 Import / Export** — backup & restore data via CSV
- **🔍 Filter & Pencarian** — filter berdasarkan status, kata kunci, dan rentang tanggal
- **💾 Penyimpanan Lokal** — SQLite, tanpa perlu server database eksternal

## 🚀 Cara Menjalankan

### Prasyarat
- Python 3.10+
- pip

### Instalasi

```bash
git clone https://github.com/MtrAldi/airdrop-tracker-MtrAldi.git
cd airdrop-tracker-MtrAldi
pip install -r requirements.txt
streamlit run airdrop_tracker_app.py
```

Buka browser ke `http://localhost:8501`.

## 📁 Struktur Project

```
.
├── airdrop_tracker_app.py   # Aplikasi Streamlit utama
├── requirements.txt         # Dependencies (streamlit, pandas)
└── airdrop_tracker.db       # Database SQLite (auto-generated)
```

> File `airdrop_tracker.db` akan otomatis dibuat saat aplikasi pertama kali dijalankan.

## 🏷️ Status Airdrop

| Status | Deskripsi |
|--------|-----------|
| `Confirmed` | Airdrop sudah resmi diumumkan tim |
| `Potential / Speculative` | Dugaan airdrop, belum ada konfirmasi |
| `Testnet Active` | Testnet sedang berjalan |
| `Active / Farming` | Lagi difarming sekarang |
| `Snapshot Taken` | Snapshot sudah diambil |
| `Verification Open` | Cek eligibilitas dibuka |
| `Claimable` | Token bisa diklaim |
| `Distributed / Done` | Selesai terdistribusi |

## 🌐 Deploy

### Streamlit Community Cloud (gratis)
1. Push repo ini ke GitHub (private/public sama saja)
2. Buka [share.streamlit.io](https://share.streamlit.io)
3. Pilih repo `MtrAldi/airdrop-tracker-MtrAldi` → branch `main` → file `airdrop_tracker_app.py`
4. Klik **Deploy**

## 🛠️ Teknologi

- [Streamlit](https://streamlit.io/) — web framework
- [Pandas](https://pandas.pydata.org/) — manipulasi data
- [SQLite](https://www.sqlite.org/) — database

## 📝 Catatan

- Data default sudah terisi 16 airdrop terpilih per September 2026 (Canopy, GIWA, Variational, Limitless, Konnex, dll). Silakan edit/hapus sesuai kebutuhan.
- **Bukan saran keuangan (NFA).** Lakukan riset sendiri sebelum farming.

## 📄 Lisensi

MIT License — bebas dipakai & dimodifikasi.
