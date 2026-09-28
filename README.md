# Airdrop Tracker Testnet

Web app untuk melacak dan memantau airdrop crypto (testnet dan mainnet) yang sedang difarming. Dibangun dengan Streamlit dan SQLite, bertema terminal hijau.

## Fitur

- **Dashboard**: metrik ringkas (total tracked, confirmed, testnet, active) plus tabel dengan badge status warna dan hitung mundur sisa hari
- **Tambah Airdrop**: input nama project, token, status, URL, tanggal mulai dan selesai, persyaratan, catatan
- **Edit / Hapus**: ubah status atau hapus entry yang sudah selesai
- **Parser Tweet**: tempel teks tweet atau thread, parser heuristik mengisi project, token, status, dan URL untuk ditinjau sebelum disimpan
- **Import / Export**: backup dan restore data lewat CSV
- **Filter dan pencarian**: saring berdasarkan status, kata kunci, dan rentang tanggal
- **Penyimpanan lokal**: SQLite, tanpa server database eksternal

## Cara Menjalankan

Prasyarat: Python 3.10+ dan pip.

```bash
git clone https://github.com/MtrAldi/airdrop-tracker.git
cd airdrop-tracker
pip install -r requirements.txt
streamlit run airdrop_tracker_app.py
```

Buka `http://localhost:8501`.

## Struktur Project

```
.
├── airdrop_tracker_app.py     # aplikasi Streamlit utama
├── initial_data.json          # 16 data seed, dipakai saat tabel masih kosong
├── requirements.txt
├── .streamlit/config.toml     # warna dasar dan font bawaan Streamlit
└── airdrop_tracker.db         # SQLite, dibuat otomatis saat pertama jalan
```

Tabel `airdrop_tracker` hanya diisi dari `initial_data.json` ketika masih kosong. Hapus `airdrop_tracker.db` untuk mengulang seeding.

## Status Airdrop

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

## Deploy

Streamlit Community Cloud, gratis. Push repo ke GitHub, buka [share.streamlit.io](https://share.streamlit.io), pilih repo `MtrAldi/airdrop-tracker`, branch `main`, file `airdrop_tracker_app.py`, lalu klik Deploy.

Filepaths di app menunjuk ke direktori source, yang di Cloud bersifat read-only. Set env var `HOME` atau jalankan di home directory yang writable sebelum deploy agar SQLite bisa dibuat.

## Teknologi

- [Streamlit](https://streamlit.io/) - web framework
- [Pandas](https://pandas.pydata.org/) - manipulasi data
- [SQLite](https://www.sqlite.org/) - database

## Catatan

- Parser tweet berbasis regex, bukan LLM. Nama project diambil dari pola "airdrop for X", kalau tidak ada lalu kata kapital pertama yang bukan kata umum. Selalu tinjau hasil parsing sebelum disimpan.
- Data seed berisi 16 airdrop per September 2026 (Canopy, GIWA, Variational, Limitless, Konnex, dan lainnya). Silakan edit atau hapus sesuai kebutuhan.
- Bukan saran keuangan. Riset sendiri sebelum farming.

## Lisensi

MIT License.
