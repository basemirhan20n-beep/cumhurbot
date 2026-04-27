# 🤖 KoopBot — Güncel Sürüm

Kooperatif projeler için otomatik ekip kurma botu.

---

## 📦 Dosyalar

| Dosya | Açıklama |
|---|---|
| `bot.py` | Ana bot — TÜM özellikler burada |
| `database.py` | SQLite veritabanı yönetimi |
| `migrate.py` | Eski veritabanını güncelle (bir kez çalıştır) |
| `.env` | Bot token |
| `requirements.txt` | Kütüphaneler |

---

## 🚀 Kurulum

### 1. Kütüphaneleri Kur
```bash
pip install -r requirements.txt
```

### 2. Token Ayarla
`.env` dosyasını düzenle:
```
BOT_TOKEN=senin_token_buraya
```

### 3. Eski Veritabanın Varsa Migrate Et
```bash
python migrate.py
```
> Yeni başlıyorsan bu adımı atla.

### 4. Botu Çalıştır
```bash
python bot.py
```

---

## ✅ Özellikler

### 👋 Hoş Geldin / Görüşürüz
- Gruba yeni biri katıldığında otomatik karşılama mesajı
- Biri ayrıldığında veda mesajı
- Çalışması için bota grup **Admin** yetkisi ver → *"Yeni üyeleri görüntüle"* iznini aç

### 😊 Sunucu Mood Sistemi
- `/mood` → 5 puanlı oy ver (😢 Berbat → 😄 Harika)
- `/moodsonuc` → Görsel bar + istatistik
- Her kullanıcı oyunu güncelleyebilir

### 💼 Kooperatif Sistemi (4 Adımlı)

```
/katil
  ↓
📝 Koop Kodunu Gir  (metin)
  ↓
💰 Ücret Seç       (buton)  100m / 200m / 300m / 500m / 800m / 1.2mr / 2.1mr / 3.4mr
  ↓
📅 Gün Seç         (buton)  2 / 4 / 6 / 8 / 10 gün
  ↓
🕐 Zaman Seç       (buton)  🌅 Gündüz / 🌙 Gece
  ↓
✅ Kayıt Tamam — 4 kişi dolunca EKİP KURULUR!
```

#### Kurallar
| Kural | Detay |
|---|---|
| Max koop | Bir kişi en fazla **4 koopa** katılabilir |
| Duplicate | Aynı (ücret + gün) kombinasyonuna 2 kez girilemez |
| Esnek | Aynı ücretle farklı gün → ✅ geçerli |
| Esnek | Farklı ücretle aynı gün → ✅ geçerli |
| Bildirim | 4 kişi dolunca **tüm üyelere** otomatik bildirim gider |

---

## 📋 Komutlar

| Komut | Açıklama |
|---|---|
| `/start` | Ana menü |
| `/yardim` | Tüm komutlar ve kurallar |
| `/katil` | Koop projesine katıl |
| `/cik` | Tüm bekleme listelerinden çık |
| `/koopum` | Aktif kooplarını gör |
| `/bekleyenler <kod>` | Kooptaki bekleyenler (kombinasyona göre gruplu) |
| `/ekipler` | Son kurulan ekipler |
| `/mood` | Sunucu ruh halini oy ver |
| `/moodsonuc` | Anlık mood istatistikleri |

---

## 🖥️ Deploy (Railway / Render / VPS)

```bash
# Railway veya Render
# Environment variable olarak ekle:
BOT_TOKEN=senin_token_buraya

# Start command:
python bot.py
```

---

## ➕ Yeni Özellik Ekleme

`database.py` ve `bot.py` içindeki sabitleri değiştir:

```python
# database.py
MAX_KOOP = 4   # Kişi başı max aktif koop

# bot.py
KOOP_KISI = 4  # Ekip büyüklüğü
FEES = ["100m", "200m", ...]   # Ücretler
DAYS = [2, 4, 6, 8, 10]        # Gün seçenekleri
TIMES = ["🌅 Gündüz", "🌙 Gece"] # Zaman dilimleri
```
