# MP3 Steganography Tool

Tugas Kecil 2 - IF4020 Kriptografi  
**Steganografi pada Berkas Audio dengan Metode Multiple-LSB**

## 📋 Deskripsi

Aplikasi web steganografi yang memungkinkan penyembunyian file rahasia ke dalam berkas audio MP3 menggunakan teknik **Multiple Least Significant Bit (LSB)** pada wilayah ancillary data frame MP3. Aplikasi ini dilengkapi dengan fitur enkripsi menggunakan **Vigenère Cipher** dan pengacakan titik penyisipan untuk meningkatkan keamanan.

## 👥 Pembuat

- **Zaki Yudhistira Candra** - 13522031
- **Edbert Eddyson Gunawan** - 13522039

## ✨ Fitur Utama

### 🔐 Keamanan
- **Enkripsi Vigenère Cipher**: Mengenkripsi payload sebelum disembunyikan
- **Pengacakan Titik Penyisipan**: Mengacak urutan frame untuk meningkatkan keamanan
- **Kunci/Seed Fleksibel**: Mendukung kunci hingga 25 karakter

### 🎵 Steganografi Audio
- **Multiple-LSB**: Mendukung 1-4 bit LSB per byte ancillary
- **Format MP3**: Fokus pada MPEG-1 Layer III
- **Ancillary Data Embedding**: Menyisipkan data pada wilayah ancillary frame MP3
- **Length-Prefixed Data**: Menggunakan marker 32-bit untuk menandai akhir data

### 🖥️ Antarmuka Web
- **Frontend Modern**: Dibangun dengan Next.js dan React
- **UI Responsif**: Menggunakan Tailwind CSS dengan desain modern
- **Audio Preview**: Pratinjau audio sebelum dan sesudah proses steganografi
- **Toast Notifications**: Notifikasi sukses menggunakan React Toastify
- **Loading States**: Indikator loading saat memproses file

## 🏗️ Arsitektur Sistem

```
├── steno-frontend/          # Frontend Next.js
│   ├── src/app/
│   │   ├── encrypt/         # Halaman enkripsi/penyembunyian
│   │   ├── decrypt/         # Halaman dekripsi/ekstraksi
│   │   └── layout.js        # Layout utama
│   ├── components/ui/       # Komponen UI
│   └── package.json
│
├── steno-backend/           # Backend Flask
│   ├── main.py             # Server Flask utama
│   └── LSB_AUDIO/          # Modul steganografi
│       ├── main_pipeline.py    # Pipeline utama
│       ├── ancillary_data.py   # Logika LSB ancillary
│       └── cipher.py           # Implementasi Vigenère
```

## 🚀 Cara Menjalankan

### Prerequisites
- **Python 3.12+** (untuk backend)
- **Node.js 18+** (untuk frontend)
- **npm atau yarn** (package manager)

### 1. Setup Backend

```bash
cd steno-backend
pip install flask flask-cors
python main.py
```

Backend akan berjalan di `http://localhost:5000`

### 2. Setup Frontend

```bash
cd steno-frontend
npm install
npm run dev
```

Frontend akan berjalan di `http://localhost:3000`

## 📖 Cara Penggunaan

### Menyembunyikan File (Encrypt)

1. **Upload File MP3**: Pilih file audio MP3 sebagai media penyembunyian
2. **Upload File Rahasia**: Pilih file yang ingin disembunyikan
3. **Konfigurasi Pengaturan**:
   - **Use Encryption**: Aktifkan untuk mengenkripsi payload
   - **Random Embedding Point**: Aktifkan untuk mengacak lokasi penyisipan
   - **LSB Bits**: Pilih jumlah bit LSB (1-4)
4. **Masukkan Kunci/Seed**: Jika encryption atau randomization diaktifkan
5. **Klik "Embed File"**: Proses penyembunyian akan dimulai
6. **Download Hasil**: File MP3 hasil steganografi dapat diunduh

### Mengekstrak File (Decrypt)

1. **Upload File MP3**: Pilih file MP3 yang berisi data tersembunyi
2. **Konfigurasi Pengaturan**: Sesuaikan dengan pengaturan saat penyembunyian
3. **Masukkan Kunci/Seed**: Jika diperlukan
4. **Klik "Extract File"**: Proses ekstraksi akan dimulai
5. **Download File**: File rahasia yang diekstrak dapat diunduh

## 🔧 Implementasi Teknis

### Steganografi LSB Ancillary

```python
# Contoh penyisipan data pada ancillary bytes
def embed_into_ancillary(mp3_bytes, frames_info, payload_bits, bits_per_byte=1):
    # Tambahkan 32-bit length prefix
    payload_length = len(payload_bits)
    length_bits = f"{payload_length:032b}"
    full_payload = length_bits + payload_bits
    
    # Sisipkan bit ke LSB ancillary bytes
    for bit_idx, bit in enumerate(full_payload):
        # Modifikasi LSB byte ancillary
        mp3_bytes[byte_pos] = (mp3_bytes[byte_pos] & 0xFE) | int(bit)
```

### Enkripsi Vigenère

```python
def vignereCipher(input_bytes, key_bytes):
    output = bytearray()
    key_length = len(key_bytes)
    for i in range(len(input_bytes)):
        key_char = key_bytes[i % key_length]
        output.append((input_bytes[i] + key_char) % 256)
    return bytes(output)
```

### Pengacakan Frame

```python
def scramble_frames_with_seed(frames_info, seed):
    random.seed(seed)
    indices = list(range(len(frames_info)))
    random.shuffle(indices) 
    return [frames_info[i] for i in indices]
```

## 🛠️ Teknologi yang Digunakan

### Backend
- **Python Flask 2.3.3**

### Frontend
- **Next.js 15.5.4**

## 📦 Dependensi

### Backend
Dependensi backend didefinisikan dalam file `requirements.txt`:

```
Flask==2.3.3
Flask-Cors==3.0.10
Werkzeug==2.3.3
```

### Frontend
Dependensi frontend didefinisikan dalam file `package.json`:

## 📝 Catatan Penting

- **Format Support**: Saat ini hanya mendukung format MP3 (MPEG-1 Layer III)
- **Ancillary Availability**: Tidak semua encoder MP3 menyisakan ancillary bytes
- **File Size Limit**: Kapasitas penyembunyian tergantung pada ketersediaan ancillary data
- **Quality Preservation**: Steganografi tidak mengubah kualitas audio secara signifikan

---

**Tugas Kecil 2 - IF4020 Kriptografi**  
Program Studi Teknik Informatika  
Institut Teknologi Bandung