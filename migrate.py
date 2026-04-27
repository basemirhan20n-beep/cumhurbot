"""
migrate.py — Mevcut koopbot.db veritabanını yeni şemaya geçirir.
Eğer bot.py'yi ilk kez çalıştırıyorsan bu dosyayı çalıştırmana GEREK YOK.
Yalnızca eski bir koopbot.db dosyan varsa bir kez çalıştır.

Kullanım:
    python migrate.py
"""

import sqlite3
import os

DB_FILE = "koopbot.db"

def migrate():
    if not os.path.exists(DB_FILE):
        print("✅ Veritabanı yok, migrate gerekmiyor. bot.py init_db() oluşturacak.")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # koop_bekleyen tablosuna eksik kolonları ekle
    mevcut_kolonlar = [
        row[1] for row in c.execute("PRAGMA table_info(koop_bekleyen)").fetchall()
    ]

    for kolon, tip in [("ucret", "TEXT"), ("gun", "INTEGER"), ("zaman", "TEXT")]:
        if kolon not in mevcut_kolonlar:
            c.execute(f"ALTER TABLE koop_bekleyen ADD COLUMN {kolon} {tip}")
            print(f"  ➕ koop_bekleyen.{kolon} eklendi")

    # ekipler tablosuna eksik kolonları ekle
    ekip_kolonlar = [
        row[1] for row in c.execute("PRAGMA table_info(ekipler)").fetchall()
    ]
    for kolon, tip in [("ucret", "TEXT"), ("gun", "INTEGER"), ("zaman", "TEXT")]:
        if kolon not in ekip_kolonlar:
            c.execute(f"ALTER TABLE ekipler ADD COLUMN {kolon} {tip}")
            print(f"  ➕ ekipler.{kolon} eklendi")

    # mood_oylar tablosunu oluştur (yoksa)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mood_oylar (
            user_id   INTEGER PRIMARY KEY,
            skor      INTEGER,
            tarih     TEXT
        )
    """)
    print("  ✅ mood_oylar tablosu hazır")

    conn.commit()
    conn.close()
    print("\n✅ Migrate tamamlandı. Artık python bot.py çalıştırabilirsin.")

if __name__ == "__main__":
    migrate()
