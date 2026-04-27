"""
KoopBot — Veritabanı Yönetimi
SQLite tabanlı kalıcı depolama
"""

import sqlite3
from datetime import datetime

DB_FILE = "koopbot.db"

FEES = ["100m", "200m", "300m", "500m", "800m", "1.2mr", "2.1mr", "3.4mr"]
DAYS = [2, 4, 6, 8, 10]
MAX_KOOP = 4  # Kişi başı maksimum aktif koop


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # ── Kullanıcılar ─────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            joined_at   TEXT
        )
    """)

    # ── Koop Bekleme Listesi ──────────────────────────────
    # ucret   : "100m", "200m" ... "3.4mr"
    # gun     : 2, 4, 6, 8, 10
    # zaman   : "Gündüz" veya "Gece"
    c.execute("""
        CREATE TABLE IF NOT EXISTS koop_bekleyen (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER,
            koop_kodu TEXT,
            ucret     TEXT,
            gun       INTEGER,
            zaman     TEXT,
            eklenme   TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    # ── Kurulan Ekipler ───────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS ekipler (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            koop_kodu  TEXT,
            ucret      TEXT,
            gun        INTEGER,
            zaman      TEXT,
            olusturma  TEXT
        )
    """)

    # ── Ekip Üyeleri ──────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS ekip_uyeleri (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ekip_id  INTEGER,
            user_id  INTEGER,
            FOREIGN KEY(ekip_id) REFERENCES ekipler(id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    # ── Sunucu Mood Oyları ────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS mood_oylar (
            user_id   INTEGER PRIMARY KEY,
            skor      INTEGER,
            tarih     TEXT
        )
    """)

    conn.commit()
    conn.close()


# ════════════════════════════════════════════════════════
#  KULLANICI
# ════════════════════════════════════════════════════════

def kayit_et(user_id: int, username: str, full_name: str):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, full_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def kullanici_getir(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row


# ════════════════════════════════════════════════════════
#  KOOP BEKLEME LİSTESİ
# ════════════════════════════════════════════════════════

def kullanici_aktif_koop_sayisi(user_id: int) -> int:
    """Kullanıcının şu an beklemede olduğu koop sayısı."""
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM koop_bekleyen WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def ayni_kombinasyon_var_mi(user_id: int, koop_kodu: str, ucret: str, gun: int) -> bool:
    """
    Aynı koop_kodu + ucret + gun kombinasyonu zaten var mı?
    (Zaman farklı olsa bile, aynı ücret+gün sayısı = duplicate)
    """
    conn = get_conn()
    row = conn.execute(
        """SELECT id FROM koop_bekleyen
           WHERE user_id=? AND koop_kodu=? AND ucret=? AND gun=?""",
        (user_id, koop_kodu, ucret, gun)
    ).fetchone()
    conn.close()
    return row is not None


def koop_ekle(user_id: int, koop_kodu: str, ucret: str, gun: int, zaman: str):
    """
    Kullanıcıyı bekleme listesine ekler.
    Önce limit ve duplicate kontrolü yapılmalı.
    """
    conn = get_conn()
    conn.execute(
        """INSERT INTO koop_bekleyen (user_id, koop_kodu, ucret, gun, zaman, eklenme)
           VALUES (?,?,?,?,?,?)""",
        (user_id, koop_kodu, ucret, gun, zaman, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def koop_bekleyenleri_getir(koop_kodu: str, ucret: str, gun: int, zaman: str) -> list:
    """Belirli bir koop kombinasyonundaki bekleyenler."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM koop_bekleyen
           WHERE koop_kodu=? AND ucret=? AND gun=? AND zaman=?
           ORDER BY eklenme ASC""",
        (koop_kodu, ucret, gun, zaman)
    ).fetchall()
    conn.close()
    return rows


def koop_koduna_gore_bekleyenler(koop_kodu: str) -> list:
    """Bir koop kodundaki tüm bekleyenler (farklı kombinasyonlar dahil)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM koop_bekleyen WHERE koop_kodu=? ORDER BY eklenme ASC",
        (koop_kodu,)
    ).fetchall()
    conn.close()
    return rows


def kullanici_kooplari(user_id: int) -> list:
    """Kullanıcının aktif bekleme listesi girişleri."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM koop_bekleyen WHERE user_id=? ORDER BY eklenme DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def koop_sil_id(kayit_id: int, user_id: int):
    """Belirli bir koop kaydını kullanıcıdan sil."""
    conn = get_conn()
    conn.execute(
        "DELETE FROM koop_bekleyen WHERE id=? AND user_id=?",
        (kayit_id, user_id)
    )
    conn.commit()
    conn.close()


def koop_listeden_cikar(user_id: int):
    """Kullanıcının tüm bekleme kayıtlarını sil."""
    conn = get_conn()
    conn.execute("DELETE FROM koop_bekleyen WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# ════════════════════════════════════════════════════════
#  EKİP OLUŞTURMA
# ════════════════════════════════════════════════════════

def ekip_olustur(koop_kodu: str, ucret: str, gun: int, zaman: str, uye_idler: list) -> int:
    """
    uye_idler: [user_id, ...]
    Bekleme listesinden çıkarır, ekip tablosuna ekler.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO ekipler (koop_kodu, ucret, gun, zaman, olusturma) VALUES (?,?,?,?,?)",
        (koop_kodu, ucret, gun, zaman, datetime.now().isoformat())
    )
    ekip_id = cur.lastrowid

    for uid in uye_idler:
        cur.execute(
            "INSERT INTO ekip_uyeleri (ekip_id, user_id) VALUES (?,?)",
            (ekip_id, uid)
        )
        cur.execute(
            "DELETE FROM koop_bekleyen WHERE user_id=? AND koop_kodu=? AND ucret=? AND gun=? AND zaman=?",
            (uid, koop_kodu, ucret, gun, zaman)
        )

    conn.commit()
    conn.close()
    return ekip_id


def ekip_getir(ekip_id: int):
    conn = get_conn()
    ekip = conn.execute("SELECT * FROM ekipler WHERE id=?", (ekip_id,)).fetchone()
    uyeler = conn.execute(
        """SELECT u.user_id, u.username, u.full_name
           FROM ekip_uyeleri eu JOIN users u ON eu.user_id=u.user_id
           WHERE eu.ekip_id=?""",
        (ekip_id,)
    ).fetchall()
    conn.close()
    return ekip, uyeler


def tum_ekipler() -> list:
    conn = get_conn()
    rows = conn.execute(
        """SELECT e.id, e.koop_kodu, e.ucret, e.gun, e.zaman, e.olusturma,
                  COUNT(eu.id) as uye_sayisi
           FROM ekipler e LEFT JOIN ekip_uyeleri eu ON e.id=eu.ekip_id
           GROUP BY e.id ORDER BY e.olusturma DESC LIMIT 20"""
    ).fetchall()
    conn.close()
    return rows


# ════════════════════════════════════════════════════════
#  MOOD SİSTEMİ
# ════════════════════════════════════════════════════════

def mood_oy_ver(user_id: int, skor: int):
    """Kullanıcının oy vermesi (günceller ya da ekler)."""
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO mood_oylar (user_id, skor, tarih) VALUES (?,?,?)",
        (user_id, skor, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def mood_sonuc() -> dict:
    """Tüm oy istatistikleri."""
    conn = get_conn()
    rows = conn.execute("SELECT skor FROM mood_oylar").fetchall()
    conn.close()

    if not rows:
        return {"toplam": 0, "ortalama": 0.0, "dagitim": {i: 0 for i in range(1, 6)}}

    skorlar = [r["skor"] for r in rows]
    dagitim = {i: skorlar.count(i) for i in range(1, 6)}
    return {
        "toplam": len(skorlar),
        "ortalama": sum(skorlar) / len(skorlar),
        "dagitim": dagitim,
    }
