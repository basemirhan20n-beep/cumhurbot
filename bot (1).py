"""
KoopBot — Kooperatif Proje Yönetim Botu
Özellikler:
  ✅ Hoş geldin / Görüşürüz (ChatMemberHandler)
  ✅ Sunucu Mood sistemi (5 puanlı oylama + istatistik)
  ✅ Kooperatif ekip kurma:
       - Ücret butonu (100m … 3.4mr)
       - Gün butonu  (2 / 4 / 6 / 8 / 10 gün)
       - Zaman       (🌅 Gündüz / 🌙 Gece)
       - Max 4 aktif koop / kişi
       - Aynı (ücret + gün) kombinasyonuna 2 kez girilemez
       - 4 kişi dolunca otomatik ekip kurulur
"""

import os
import logging
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMemberUpdated,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import database as db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

# ─── ConversationHandler durumları ───────────────────────
(
    KOOP_KODU,   # Koop kodu girişi (metin)
    KOOP_UCRET,  # Ücret seçimi (buton)
    KOOP_GUN,    # Gün seçimi (buton)
    KOOP_ZAMAN,  # Zaman seçimi (buton)
) = range(4)

# ─── Sabitler ────────────────────────────────────────────
KOOP_KISI = 4   # Ekip büyüklüğü

FEES = ["100m", "200m", "300m", "500m", "800m", "1.2mr", "2.1mr", "3.4mr"]
DAYS = [2, 4, 6, 8, 10]
TIMES = ["🌅 Gündüz", "🌙 Gece"]

MOOD_LABELS = {
    1: "😢 Berbat",
    2: "😕 Kötü",
    3: "😐 Orta",
    4: "🙂 İyi",
    5: "😄 Harika",
}


# ════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ════════════════════════════════════════════════════════

def kaydet(update: Update):
    u = update.effective_user
    if u:
        db.kayit_et(u.id, u.username or "", u.full_name or "")


def ana_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Koop'a Katıl",   callback_data="koop_katil")],
        [
            InlineKeyboardButton("📋 Kooplarım",   callback_data="koopum"),
            InlineKeyboardButton("🏆 Ekipler",     callback_data="ekip_listesi"),
        ],
        [
            InlineKeyboardButton("😊 Mood Ver",    callback_data="mood_menu"),
            InlineKeyboardButton("📊 Mood Sonuç",  callback_data="mood_sonuc"),
        ],
        [InlineKeyboardButton("❓ Yardım",          callback_data="yardim")],
    ])


def iptal_butonu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ İptal", callback_data="iptal")]
    ])


def geri_iptal(geri_data: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Geri",  callback_data=geri_data),
            InlineKeyboardButton("❌ İptal", callback_data="iptal"),
        ]
    ])


def mood_cubuklari(sonuc: dict) -> str:
    ort = sonuc["ortalama"]
    dolu = round(ort)
    bar = "█" * dolu + "░" * (5 - dolu)
    emoji = MOOD_LABELS.get(dolu, "😐")
    dagitim = "  ".join(
        f"{MOOD_LABELS[i].split()[0]} {sonuc['dagitim'][i]}" for i in range(1, 6)
    )
    return (
        f"`{bar}` {ort:.1f}/5 {emoji}\n"
        f"Oy veren: *{sonuc['toplam']}* kişi\n"
        f"{dagitim}"
    )


# ════════════════════════════════════════════════════════
#  HOŞ GELDİN / GÖRÜŞÜRÜZ  (ChatMemberHandler)
# ════════════════════════════════════════════════════════

async def uye_takip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Gruba katılan ve ayrılan üyeleri takip et."""
    result: ChatMemberUpdated = update.chat_member
    if result is None:
        return

    eski = result.old_chat_member.status
    yeni = result.new_chat_member.status
    uye  = result.new_chat_member.user

    # Katılma
    GIRIS = {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED}
    if eski in GIRIS and yeni == ChatMemberStatus.MEMBER:
        db.kayit_et(uye.id, uye.username or "", uye.full_name or "")
        await ctx.bot.send_message(
            chat_id=result.chat.id,
            text=(
                f"👋 *Hoş geldin, {uye.first_name}!*\n\n"
                f"🎉 Sunucumuza katıldığın için çok mutluyuz!\n"
                f"📋 /yardim yazarak komutlara göz at.\n"
                f"💼 Kooperatif projeye katılmak için /katil komutunu dene!"
            ),
            parse_mode="Markdown",
        )

    # Ayrılma
    elif eski == ChatMemberStatus.MEMBER and yeni in {
        ChatMemberStatus.LEFT, ChatMemberStatus.BANNED
    }:
        await ctx.bot.send_message(
            chat_id=result.chat.id,
            text=f"👋 Görüşürüz, *{uye.first_name}*! Tekrar bekleriz. 💙",
            parse_mode="Markdown",
        )


# ════════════════════════════════════════════════════════
#  TEMEL KOMUTLAR
# ════════════════════════════════════════════════════════

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kaydet(update)
    isim = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Merhaba *{isim}*!\n\n"
        f"Ben *KoopBot*'um — Kooperatif projeler için ekip kurma botuyum.\n\n"
        f"📌 *Nasıl çalışır?*\n"
        f"1️⃣ Koop kodunu gir\n"
        f"2️⃣ Ücret, gün sayısı ve zaman dilimini seç\n"
        f"3️⃣ {KOOP_KISI} kişi dolunca ekip otomatik kurulur ✅\n\n"
        f"Aşağıdan seçim yap 👇",
        parse_mode="Markdown",
        reply_markup=ana_menu(),
    )


async def yardim_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 *Komutlar*\n\n"
        "/start — Ana menü\n"
        "/yardim — Bu mesaj\n"
        "/katil — Koop projesine katıl\n"
        "/cik — Tüm bekleme listelerinden çık\n"
        "/koopum — Aktif kooplarını gör\n"
        "/bekleyenler `<kod>` — Kooptaki bekleyenler\n"
        "/ekipler — Son kurulan ekipler\n"
        "/mood — Sunucu ruh halini oy ver\n"
        "/moodsonuc — Anlık mood istatistikleri\n\n"
        "📌 *Kurallar:*\n"
        f"• Bir kişi en fazla *{db.MAX_KOOP} koopa* katılabilir\n"
        "• Aynı ücret + aynı gün kombinasyonuna 2 kez girilemez\n"
        f"• {KOOP_KISI} kişi dolunca ekip otomatik kurulur"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=ana_menu()
        )
    else:
        await update.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=ana_menu()
        )


# ════════════════════════════════════════════════════════
#  MOOD SİSTEMİ
# ════════════════════════════════════════════════════════

async def mood_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"mood_oy_{skor}")]
        for skor, label in MOOD_LABELS.items()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")])
    msg = "😊 *Bugün sunucunun ruh hali nasıl?*\n\nAşağıdan oyunu ver:"

    if update.callback_query:
        await update.callback_query.message.reply_text(
            msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            msg, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def moodsonuc_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sonuc = db.mood_sonuc()
    if sonuc["toplam"] == 0:
        metin = "📊 *Mood Sonuçları*\n\nHenüz oy kullanılmadı."
    else:
        metin = f"📊 *SUNUCU MOOD DURUMU*\n\n{mood_cubuklari(sonuc)}"

    if update.callback_query:
        await update.callback_query.message.reply_text(
            metin, parse_mode="Markdown", reply_markup=ana_menu()
        )
    else:
        await update.message.reply_text(
            metin, parse_mode="Markdown", reply_markup=ana_menu()
        )


# ════════════════════════════════════════════════════════
#  KOOP CONVERSATION HANDLER
# ════════════════════════════════════════════════════════

async def katil_baslat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Adım 0 — Koop kodunu sor."""
    kaydet(update)
    ctx.user_data.clear()

    send = (
        update.callback_query.message.reply_text
        if update.callback_query
        else update.message.reply_text
    )
    if update.callback_query:
        await update.callback_query.answer()

    await send(
        "📝 *Adım 1/4 — Koop Kodu*\n\n"
        "Katılmak istediğin koop kodunu yaz:\n"
        "_(örnek: PROJE2024, KOOP-A1)_",
        parse_mode="Markdown",
        reply_markup=iptal_butonu(),
    )
    return KOOP_KODU


async def koop_kodu_al(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Adım 1 — Ücret seç."""
    kodu = update.message.text.strip().upper()
    if len(kodu) < 2:
        await update.message.reply_text(
            "⚠️ Geçersiz kod. En az 2 karakter olmalı. Tekrar gir:",
            reply_markup=iptal_butonu(),
        )
        return KOOP_KODU

    # Limit kontrolü
    user_id = update.effective_user.id
    aktif = db.kullanici_aktif_koop_sayisi(user_id)
    if aktif >= db.MAX_KOOP:
        await update.message.reply_text(
            f"❌ *Koop limitine ulaştın!*\n\n"
            f"Bir kişi en fazla *{db.MAX_KOOP} koopa* katılabilir.\n"
            f"Çıkmak için /cik veya /koopum komutunu kullan.",
            parse_mode="Markdown",
            reply_markup=ana_menu(),
        )
        return ConversationHandler.END

    ctx.user_data["koop_kodu"] = kodu
    mevcut = db.koop_koduna_gore_bekleyenler(kodu)

    keyboard = [
        [InlineKeyboardButton(f"💰 {fee}", callback_data=f"ucret_{fee}")]
        for fee in FEES
    ]
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="iptal")])

    await update.message.reply_text(
        f"✅ Koop kodu: *{kodu}*\n"
        f"👥 Bu kodda bekleyen: *{len(mevcut)}* kayıt\n\n"
        f"💰 *Adım 2/4 — Ücret seç:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return KOOP_UCRET


async def ucret_sec(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Adım 2 — Gün sayısı seç."""
    q = update.callback_query
    await q.answer()
    ucret = q.data.replace("ucret_", "")
    ctx.user_data["ucret"] = ucret

    keyboard = [
        [InlineKeyboardButton(f"📅 {gun} Gün", callback_data=f"gun_{gun}")]
        for gun in DAYS
    ]
    keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="geri_ucret"),
                     InlineKeyboardButton("❌ İptal", callback_data="iptal")])

    await q.message.edit_text(
        f"✅ Koop kodu: *{ctx.user_data['koop_kodu']}*\n"
        f"✅ Ücret: *{ucret}*\n\n"
        f"📅 *Adım 3/4 — Gün sayısı seç:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return KOOP_GUN


async def gun_sec(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Adım 3 — Zaman dilimi seç."""
    q = update.callback_query
    await q.answer()
    gun = int(q.data.replace("gun_", ""))
    ctx.user_data["gun"] = gun

    kood  = ctx.user_data["koop_kodu"]
    ucret = ctx.user_data["ucret"]
    user_id = q.from_user.id

    # Duplicate kontrolü
    if db.ayni_kombinasyon_var_mi(user_id, kood, ucret, gun):
        await q.message.edit_text(
            f"⚠️ *Duplicate Kombinasyon!*\n\n"
            f"Koop *{kood}* için *{ucret} / {gun} gün* kombinasyonuna zaten kayıtlısın.\n\n"
            f"Farklı ücret veya farklı gün sayısı seçebilirsin.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Yeni Deneme", callback_data="koop_katil")],
                [InlineKeyboardButton("❌ Kapat", callback_data="iptal")],
            ]),
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(zaman, callback_data=f"zaman_{i}")]
        for i, zaman in enumerate(TIMES)
    ]
    keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="geri_gun"),
                     InlineKeyboardButton("❌ İptal", callback_data="iptal")])

    await q.message.edit_text(
        f"✅ Koop kodu: *{kood}*\n"
        f"✅ Ücret:     *{ucret}*\n"
        f"✅ Süre:      *{gun} gün*\n\n"
        f"🕐 *Adım 4/4 — Zaman dilimi seç:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return KOOP_ZAMAN


async def zaman_sec(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Adım 4 — Kaydı tamamla. 4 kişi dolunca ekip kur."""
    q = update.callback_query
    await q.answer()
    idx   = int(q.data.replace("zaman_", ""))
    zaman = TIMES[idx]

    kood    = ctx.user_data["koop_kodu"]
    ucret   = ctx.user_data["ucret"]
    gun     = ctx.user_data["gun"]
    user_id = q.from_user.id

    db.koop_ekle(user_id, kood, ucret, gun, zaman)
    bekleyenler = db.koop_bekleyenleri_getir(kood, ucret, gun, zaman)
    kalan = KOOP_KISI - len(bekleyenler)

    if kalan > 0:
        await q.message.edit_text(
            f"✅ *Kayıt Tamam!*\n\n"
            f"📌 Koop Kodu: `{kood}`\n"
            f"💰 Ücret:     *{ucret}*\n"
            f"📅 Süre:      *{gun} gün*\n"
            f"🕐 Zaman:     {zaman}\n\n"
            f"👥 Doluluk: *{len(bekleyenler)}/{KOOP_KISI}*\n"
            f"⏳ Ekip için *{kalan} kişi daha* bekleniyor...",
            parse_mode="Markdown",
            reply_markup=ana_menu(),
        )
    else:
        # ✅ DOLDU — Ekip kur!
        uye_idler = [r["user_id"] for r in bekleyenler]
        ekip_id = db.ekip_olustur(kood, ucret, gun, zaman, uye_idler)
        _, ekip_uyeler = db.ekip_getir(ekip_id)

        satirlar = ""
        for i, u in enumerate(ekip_uyeler, 1):
            mention = f"@{u['username']}" if u["username"] else u["full_name"]
            satirlar += f"  {i}. {mention}\n"

        ekip_mesaji = (
            f"🎉 *EKİP KURULDU!*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 Koop Kodu: `{kood}`\n"
            f"💰 Ücret:     *{ucret}*\n"
            f"📅 Süre:      *{gun} gün*\n"
            f"🕐 Zaman:     {zaman}\n"
            f"🆔 Ekip No:   *#{ekip_id}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👥 *Üyeler:*\n{satirlar}"
            f"━━━━━━━━━━━━━━━━━━"
        )

        buton = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Ekip Detayı", callback_data=f"ekip_{ekip_id}")],
            [InlineKeyboardButton("➕ Yeni Koop",   callback_data="koop_katil")],
        ])

        for u in ekip_uyeler:
            try:
                await ctx.bot.send_message(
                    chat_id=u["user_id"],
                    text=ekip_mesaji,
                    parse_mode="Markdown",
                    reply_markup=buton,
                )
            except Exception:
                pass

    return ConversationHandler.END


# Geri butonları
async def geri_ucret(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kood = ctx.user_data.get("koop_kodu", "?")
    keyboard = [
        [InlineKeyboardButton(f"💰 {fee}", callback_data=f"ucret_{fee}")]
        for fee in FEES
    ]
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="iptal")])
    await q.message.edit_text(
        f"✅ Koop kodu: *{kood}*\n\n💰 *Adım 2/4 — Ücret seç:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return KOOP_UCRET


async def geri_gun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kood  = ctx.user_data.get("koop_kodu", "?")
    ucret = ctx.user_data.get("ucret", "?")
    keyboard = [
        [InlineKeyboardButton(f"📅 {gun} Gün", callback_data=f"gun_{gun}")]
        for gun in DAYS
    ]
    keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="geri_ucret"),
                     InlineKeyboardButton("❌ İptal", callback_data="iptal")])
    await q.message.edit_text(
        f"✅ Koop kodu: *{kood}*\n"
        f"✅ Ücret:     *{ucret}*\n\n"
        f"📅 *Adım 3/4 — Gün sayısı seç:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return KOOP_GUN


async def katil_iptal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "❌ İşlem iptal edildi.", reply_markup=ana_menu()
        )
    else:
        await update.message.reply_text("❌ İşlem iptal edildi.", reply_markup=ana_menu())
    return ConversationHandler.END


# ════════════════════════════════════════════════════════
#  DİĞER KOMUTLAR
# ════════════════════════════════════════════════════════

async def cik_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının tüm koop kayıtlarını sil."""
    user_id = update.effective_user.id
    db.koop_listeden_cikar(user_id)
    await update.message.reply_text(
        "✅ Tüm bekleme listelerinden çıkarıldın.",
        reply_markup=ana_menu(),
    )


async def koopum_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının aktif koopları."""
    user_id = update.effective_user.id
    kayitlar = db.kullanici_kooplari(user_id)

    if not kayitlar:
        metin = "📭 Şu an aktif bir koop kaydın yok."
    else:
        satirlar = ""
        for i, k in enumerate(kayitlar, 1):
            satirlar += (
                f"  {i}. `{k['koop_kodu']}` — *{k['ucret']}* — "
                f"{k['gun']} gün — {k['zaman']}\n"
            )
        metin = (
            f"💼 *Aktif Koopların* ({len(kayitlar)}/{db.MAX_KOOP})\n\n"
            f"{satirlar}\n"
            f"Bir kooptan çıkmak için /cik yaz."
        )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            metin, parse_mode="Markdown", reply_markup=ana_menu()
        )
    else:
        await update.message.reply_text(
            metin, parse_mode="Markdown", reply_markup=ana_menu()
        )


async def bekleyenler_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ Kullanım: `/bekleyenler KOOP_KODU`", parse_mode="Markdown"
        )
        return

    kood = ctx.args[0].strip().upper()
    bekleyenler = db.koop_koduna_gore_bekleyenler(kood)

    if not bekleyenler:
        await update.message.reply_text(
            f"❌ `{kood}` kodunda bekleyen yok.", parse_mode="Markdown"
        )
        return

    # Kombinasyonlara göre grupla
    gruplar: dict[str, list] = {}
    for b in bekleyenler:
        anahtar = f"{b['ucret']} / {b['gun']} gün / {b['zaman']}"
        gruplar.setdefault(anahtar, []).append(b)

    metin = f"👥 *{kood}* — Bekleyenler\n\n"
    for combo, uyeler in gruplar.items():
        metin += f"🔹 *{combo}* ({len(uyeler)}/{KOOP_KISI})\n"
        for u in uyeler:
            kullanici = db.kullanici_getir(u["user_id"])
            mention = (
                f"@{kullanici['username']}" if kullanici and kullanici["username"]
                else (kullanici["full_name"] if kullanici else str(u["user_id"]))
            )
            metin += f"    • {mention}\n"
        metin += "\n"

    await update.message.reply_text(metin, parse_mode="Markdown")


async def ekipler_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ekipler = db.tum_ekipler()
    if not ekipler:
        metin = "Henüz oluşturulmuş ekip yok."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(metin)
        else:
            await update.message.reply_text(metin)
        return

    butonlar = []
    for e in ekipler:
        tarih = e["olusturma"][:10]
        butonlar.append([
            InlineKeyboardButton(
                f"#{e['id']} — {e['koop_kodu']} | {e['ucret']} | {e['gun']}g | {e['zaman']} ({tarih})",
                callback_data=f"ekip_{e['id']}",
            )
        ])

    markup = InlineKeyboardMarkup(butonlar)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "🏆 *Son Ekipler* — detay için tıkla:",
            parse_mode="Markdown",
            reply_markup=markup,
        )
    else:
        await update.message.reply_text(
            "🏆 *Son Ekipler* — detay için tıkla:",
            parse_mode="Markdown",
            reply_markup=markup,
        )


# ════════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ════════════════════════════════════════════════════════

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    # ── MOOD ──────────────────────────────────────────────
    if d == "mood_menu":
        await mood_cmd(update, ctx)

    elif d == "mood_sonuc":
        await moodsonuc_cmd(update, ctx)

    elif d.startswith("mood_oy_"):
        skor = int(d.replace("mood_oy_", ""))
        db.mood_oy_ver(q.from_user.id, skor)
        sonuc = db.mood_sonuc()
        await q.message.edit_text(
            f"✅ Oyun kaydedildi: *{MOOD_LABELS[skor]}*\n\n"
            f"📊 *Güncel Mood*\n{mood_cubuklari(sonuc)}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]
            ]),
        )

    # ── KOOP ──────────────────────────────────────────────
    elif d == "koopum":
        await koopum_cmd(update, ctx)

    elif d == "ekip_listesi":
        await ekipler_cmd(update, ctx)

    elif d.startswith("ekip_"):
        ekip_id = int(d.split("_")[1])
        ekip, uyeler = db.ekip_getir(ekip_id)
        if not ekip:
            await q.message.reply_text("❌ Ekip bulunamadı.")
            return
        satirlar = ""
        for i, u in enumerate(uyeler, 1):
            mention = f"@{u['username']}" if u["username"] else u["full_name"]
            satirlar += f"  {i}. {mention}\n"
        await q.message.reply_text(
            f"🏆 *Ekip #{ekip_id}*\n"
            f"📌 Koop: `{ekip['koop_kodu']}`\n"
            f"💰 Ücret: *{ekip['ucret']}*\n"
            f"📅 Süre: *{ekip['gun']} gün*\n"
            f"🕐 Zaman: {ekip['zaman']}\n"
            f"📅 Kurulma: {ekip['olusturma'][:16]}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👥 *Üyeler:*\n{satirlar}",
            parse_mode="Markdown",
        )

    # ── GENEL ─────────────────────────────────────────────
    elif d == "yardim":
        await yardim_cmd(update, ctx)

    elif d == "ana_menu":
        await q.message.edit_text(
            "Ana Menü 👇", reply_markup=ana_menu()
        )

    elif d == "iptal":
        ctx.user_data.clear()
        await q.message.edit_text("❌ İşlem iptal edildi.", reply_markup=ana_menu())


# ════════════════════════════════════════════════════════
#  GENEL MESAJ HANDLER
# ════════════════════════════════════════════════════════

async def genel_mesaj(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kaydet(update)
    await update.message.reply_text(
        "🤖 Menüden bir seçenek seç ya da /katil yazarak koop projesine katıl!",
        reply_markup=ana_menu(),
    )


# ════════════════════════════════════════════════════════
#  UYGULAMA BAŞLATMA
# ════════════════════════════════════════════════════════

def main():
    db.init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    # ── Koop ConversationHandler ──────────────────────────
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("katil", katil_baslat),
            CallbackQueryHandler(katil_baslat, pattern="^koop_katil$"),
        ],
        states={
            KOOP_KODU:  [MessageHandler(filters.TEXT & ~filters.COMMAND, koop_kodu_al)],
            KOOP_UCRET: [CallbackQueryHandler(ucret_sec, pattern=r"^ucret_"),
                         CallbackQueryHandler(geri_ucret, pattern="^geri_ucret$")],
            KOOP_GUN:   [CallbackQueryHandler(gun_sec, pattern=r"^gun_\d+$"),
                         CallbackQueryHandler(geri_gun,   pattern="^geri_gun$"),
                         CallbackQueryHandler(geri_ucret, pattern="^geri_ucret$")],
            KOOP_ZAMAN: [CallbackQueryHandler(zaman_sec, pattern=r"^zaman_\d+$"),
                         CallbackQueryHandler(geri_gun,   pattern="^geri_gun$")],
        },
        fallbacks=[
            CommandHandler("iptal", katil_iptal),
            CallbackQueryHandler(katil_iptal, pattern="^iptal$"),
        ],
        per_message=False,
    )

    # ── Handler'lar ───────────────────────────────────────
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("yardim",       yardim_cmd))
    app.add_handler(CommandHandler("cik",          cik_cmd))
    app.add_handler(CommandHandler("koopum",       koopum_cmd))
    app.add_handler(CommandHandler("bekleyenler",  bekleyenler_cmd))
    app.add_handler(CommandHandler("ekipler",      ekipler_cmd))
    app.add_handler(CommandHandler("mood",         mood_cmd))
    app.add_handler(CommandHandler("moodsonuc",    moodsonuc_cmd))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Hoş geldin / Görüşürüz — chat_member güncellemeleri
    app.add_handler(
        ChatMemberHandler(uye_takip, ChatMemberHandler.CHAT_MEMBER)
    )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, genel_mesaj))

    print("🤖 KoopBot başlatıldı...")
    app.run_polling(allowed_updates=["message", "callback_query", "chat_member"])


if __name__ == "__main__":
    main()
