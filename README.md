**YouTube Logger – README**

**Deskripsi Singkat**
YouTube Logger adalah ekstensi Firefox (juga kompatibel dengan Chrome) yang secara otomatis mencatat URL video YouTube yang sedang terbuka atau diputar pada browser, lalu mengirimkannya melalui WebSocket ke server Python. Server akan melakukan filtrasi dan pencatatan detail video, memisahkan antara video musik dan non-musik dengan menggunakan yt-dlp.

---

## 📁 Struktur Proyek

```
├── background.js       # Script background pada ekstensi
├── popup.html         # UI popup ekstensi
├── popup.js           # Logika frontend popup
├── style.css          # (Opsional) Style untuk popup
├── manifest.json      # Konfigurasi manifest ekstensi
├── icons/             # Folder ikon ekstensi
│   └── icon128.png
└── server_ektension_firefox.py  # Script server Python
```

---

## 🔧 Prasyarat

1. **Browser**: Firefox (dengan manifest v2), atau Chrome (dengan sedikit penyesuaian).
2. **Python 3.7+**
3. **Dependencies Python**:

   * `websockets`
   * `yt_dlp`
4. **Port WebSocket**: Default mencoba port `8001–8005` pada `localhost`.

Instalasi dependencies server:

```bash
pip install websockets yt-dlp
```

---

## 🚀 Instalasi & Penggunaan

1. **Ekstensi**
   a. Buka `about:debugging` di Firefox → "Load Temporary Add-on..." → pilih `manifest.json`.
   b. Aktifkan ekstensi dan buka popup untuk memeriksa status.

2. **Server Python**
   a. Jalankan server:

   ```bash
   python server_ektension_firefox.py
   ```

   b. Server akan mendengarkan WebSocket pada port 8001–8005 dan menunggu koneksi ekstensi.

3. **Mencatat Video**

   * Saat Anda membuka atau memutar video YouTube, ekstensi akan otomatis mengirim URL ke server.
   * Server akan memroses metadata dan mencatat ke file `tab_log.txt` (musik) atau `un_log.txt` (non-musik).

---

## 📜 Penjelasan Kode

### 1. `background.js`

* **Konstanta & Variabel**

  * `WS_SERVER_PORTS`: Daftar port WebSocket (8001–8005).
  * `CONNECTION_CODE`: Kode handshake antara ekstensi dan server.
  * `socket`, `socketConnected`, `connectedPort`: Status koneksi WebSocket.

* **Fungsi Utama**

  * `isConnected()`: Mengecek koneksi WebSocket aktif.
  * `getConnectedPort()`: Mengembalikan port yang terhubung.
  * `cleanupSocket()`: Menutup dan mereset socket jika perlu.
  * `connectToServer(callback)`: Mencoba koneksi berurutan ke port yang tersedia. Menggunakan `chrome.storage.local.enabled` untuk menghentikan/restart proses saat opsi on/off.
  * `sendUrl(url)`: Mengirim URL video ke server, memastikan format valid (`youtube.com/watch`), melakukan reconnect jika koneksi terputus.
  * `scanTabs()`: Memindai semua tab browser yang aktif, mengirim ulang URL YouTube.

* **Event Listener**

  * `chrome.webRequest.onCompleted`: Deteksi request yang selesai, kirim URL YouTube jika match.
  * `chrome.runtime.onStartup`: Saat browser start, panggil `connectToServer()`.
  * `chrome.storage.onChanged`: Respon saat user toggle on/off di popup.
  * Inisialisasi awal: baca `enabled` → jika true, langsung connect.
  * Mengekspos `isConnected`, `getConnectedPort`, `scanTabs` ke `window` untuk akses popup.

### 2. `manifest.json`

Menentukan manifest v2:

* `permissions`: `tabs`, `storage`, `webNavigation`, `webRequest`, `<all_urls>`.
* `background.scripts`: `background.js`, `persistent: true`.
* `browser_action`: Popup, title, ikon.

### 3. `popup.html` & `popup.js`

**popup.html**

* Struktur HTML sederhana, memuat CSS dan `popup.js`.

**popup.js**

* **UI Elements**: Status koneksi, port, tombol toggle, daftar tab YouTube.
* `refreshUI()`: Ambil status `enabled` dan `isConnected` dari background, update teks + warna.
* `updateTabList()`: Query semua tab, filter URL YouTube, buat/mutakhirkan list item dengan animasi marquee jika teks panjang.
* `toggleBtn` listener: Toggle opsi `enabled` di `chrome.storage.local`.
* Refresh UI setiap 2 detik untuk sinkronisasi real-time.

### 4. `server_ektension_firefox.py`

* **Konfigurasi & Logger**

  * `MUSIC_KEYWORDS`: Kata kunci identifikasi video musik.
  * File log: `tab_log.txt` (musik), `un_log.txt` (non-musik), `logging.txt` (logger).

* **Inisialisasi**

  * `load_logged_links()`, `load_un_logged_links()`: Muat link yang sudah pernah diproses.

* **Fungsi Asinkron**

  * `canonicalize_youtube_url(url)`: Ekstraksi ID video, normalisasi ke format `https://www.youtube.com/watch?v=VIDEO_ID`.
  * `extract_info(canonical_url)`: Gunakan `yt_dlp.YoutubeDL` untuk mengambil metadata (tanpa download video).
  * `is_music_video(info)`: Heuristik dari judul, tag, deskripsi, kategori, atau nama channel untuk menentukan apakah video musik.

* **WebSocket Handler**

  * Menerima handshake kode (`EXPECTED_CODE`). Set port utama (`successful_port`), lalu terima pesan JSON berisi `url`.
  * Canonicalize → periksa duplikasi → ekstrak metadata → log ke file sesuai hasil deteksi musik.
  * Tangani error handshake, JSON invalid, koneksi tertutup, dan multi-port fallback.

* **Main Event Loop**

  * Jalankan server websockets pada semua port di `PORTS_TO_TRY`.
  * Tunggu handshake pertama → tutup server lain → jalankan server utama hingga user tekan `q`.

---

## 🔍 Debugging & Tips

* Pastikan port 8001–8005 tidak diblokir oleh firewall.
* Cek `logging.txt` untuk detail error.
* Pengaturan `enabled` dapat diubah langsung di "Storage Inspector" (DevTools).

---

**Lisensi**
Proyek ini dirilis di bawah lisensi MIT. Silakan modifikasi sesuai kebutuhan.

**Kontributor**

* Nama Anda
* Email / GitHub

---

© 2025 YouTube Logger Project
