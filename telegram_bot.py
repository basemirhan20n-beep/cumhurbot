#!/usr/bin/env python3
"""
🤖 Kooperatif & Topluluk Telegram Botu
Özellikler:
  - Hoş geldin / Görüşürüz mesajları
  - Sunucu Mood ölçümü
  - Kooperatif ekip kurma sistemi (ücret + gün + gece/gündüz seçimi)
"""

import json
import os
import logging
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMemberUpdated,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ──────────────────────────────────────────────
# YAPILANDIRMA
# ──────────────────────────────────────────────
BOT_TOKEN = "BURAYA_TOKEN_YAZ"          # @BotFather'dan alınan token
DATA_FILE = "bot_data.json"              # Kalıcı veri dosyası

FEES  = ["100m", "200m", "300m", "500m", "800m", "1.2mr", "2.1mr", "3.4mr"]
DAYS  = [2, 4, 6, 8, 10]
TIMES = ["🌅 Gündüz", "🌙 Gece"]
MOODS = {
    "1": "😢 Berbat",
    "2": "😕 Kötü",
    "3": "😐 Orta",
    "4": "🙂 İyi",
    "5": "😄 Harika",
}
MAX_COOPS = 4  # Bir kişi en fazla 4 koopa katılabilir

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# VERİ YÖNETİMİ
# ──────────────────────────────────────────────
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"coops": {}, "mood_votes": {}, "teams": {}}


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_data()


# ──────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ──────────────────────────────────────────────
def coop_key(fee: str, days: int, time: str) -> str:
    """Eşsiz koop anahtarı."""
    return f"{fee}_{days}gün_{time.replace(' ', '')}"


def user_coop_list(user_id: str) -> list:
    return data["coops"].get(user_id, [])


def coop_team_members(key: str) -> list:
    return data["teams"].get(key, [])


def mood_average() -> str:
    votes = list(data["mood_votes"].values())
    if not votes:
        return "Henüz oy yok."
    avg = sum(votes) / len(votes)
    bar = "".join(["█" if i < round(avg) else "░" for i in range(5)])
    emoji = list(MOODS.values())[round(avg) - 1]
    return f"{bar}  {avg:.1f}/5  {emoji}"


# ──────────────────────────────────────────────
# HOŞ GELDİN / GÖRÜŞÜRÜZ
# ──────────────────────────────────────────────
async def track_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result is None:
        return
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    member = result.new_chat_member.user

    # Katılma
    if old_status in (
        ChatMemberStatus.LEFT,
        ChatMemberStatus.BANNED,
        ChatMemberStatus.RESTRICTED,
    ) and new_status == ChatMemberStatus.MEMBER:
        await context.bot.send_message(
            chat_id=result.chat.id,
            text=(
                f"👋 *Hoş geldin, {member.first_name}!*\n\n"
                f"🎉 Sunucumuza katıldığın için çok mutluyuz!\n"
                f"📋 `/yardim` yazarak tüm komutları görebilirsin.\n"
                f"💼 Kooperatif kurmak için `/koop` komutunu dene!"
            ),
            parse_mode="Markdown",
        )

    # Ayrılma
    elif old_status == ChatMemberStatus.MEMBER and new_status in (
        ChatMemberStatus.LEFT,
        ChatMemberStatus.BANNED,
    ):
        await context.bot.send_message(
            chat_id=result.chat.id,
            text=(
                f"👋 Görüşürüz, *{member.first_name}*!\n"
                f"Umarız yakında tekrar görüşürüz. 💙"
            ),
            parse_mode="Markdown",
        )


# ──────────────────────────────────────────────
# KOMUTLAR
# ──────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Aktif!*\n\n"
        "Mevcut komutlar:\n"
        "• `/yardim` — Tüm komutlar\n"
        "• `/koop` — Kooperatif kur/görüntüle\n"
        "• `/kooplistesi` — Tüm açık kooplar\n"
        "• `/mood` — Sunucu ruh halini oy ver\n"
        "• `/moodsonuc` — Güncel mood sonuçları",
        parse_mode="Markdown",
    )


async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *KOMUT LİSTESİ*\n\n"
        "🔹 `/start` — Botu başlat\n"
        "🔹 `/yardim` — Bu menüyü göster\n\n"
        "💼 *KOOPERATIF*\n"
        "🔹 `/koop` — Yeni koop oluştur ya da katıl\n"
        "🔹 `/kooplistesi` — Tüm açık koopları listele\n"
        "🔹 `/koopum` — Katıldığın koopları gör\n"
        "🔹 `/koopcik` — Koop'tan çık\n\n"
        "😊 *SUNUCU MOOD*\n"
        "🔹 `/mood` — Ruh halini oy ver\n"
        "🔹 `/moodsonuc` — Anlık mood göster\n\n"
        "📌 *Kurallar:*\n"
        "• Bir kişi en fazla 4 koopa katılabilir\n"
        "• Aynı ücret + aynı gün kombinasyonuna 2 kez girilemez\n"
        "• Farklı gün veya farklı ücretle yeni koop açılabilir",
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# MOOD SİSTEMİ
# ──────────────────────────────────────────────
async def mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"mood_{score}")]
        for score, label in MOODS.items()
    ]
    await update.message.reply_text(
        "😊 *Bugün sunucunun ruh hali nasıl?*\nOyunu ver:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def mood_sonuc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    toplam = len(data["mood_votes"])
    await update.message.reply_text(
        f"📊 *SUNUCU MOOD SONUÇLARI*\n\n"
        f"Oy veren: {toplam} kişi\n"
        f"Ortalama: {mood_average()}",
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# KOOPERATIF SİSTEMİ
# ──────────────────────────────────────────────
async def koop_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"💰 {fee}", callback_data=f"koop_fee_{fee}")]
        for fee in FEES
    ]
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="koop_iptal")])
    await update.message.reply_text(
        "💼 *YENİ KOOPERATIF*\n\n"
        "Adım 1/3 — Ücret seç:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def koop_listesi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teams = data.get("teams", {})
    if not teams:
        await update.message.reply_text("📭 Şu an açık koop yok.")
        return

    msg = "📋 *AÇIK KOOPLAR*\n\n"
    for key, members in teams.items():
        parts = key.split("_")
        fee = parts[0]
        days = parts[1]
        time_part = parts[2] if len(parts) > 2 else ""
        msg += f"🔹 `{fee}` — {days} — {time_part} — {len(members)} üye\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def koopum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_coops = data["coops"].get(user_id, [])

    if not user_coops:
        await update.message.reply_text("📭 Henüz hiçbir koopa katılmadın.")
        return

    msg = "💼 *KATILDIĞIN KOOPLAR*\n\n"
    for i, c in enumerate(user_coops, 1):
        key = coop_key(c["fee"], c["days"], c["time"])
        team_size = len(coop_team_members(key))
        msg += (
            f"{i}. `{c['fee']}` — {c['days']} gün — {c['time']}\n"
            f"   👥 {team_size} üye | 📅 {c.get('tarih', '-')}\n\n"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def koop_cik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_coops_list = data["coops"].get(user_id, [])

    if not user_coops_list:
        await update.message.reply_text("📭 Çıkabileceğin bir koop yok.")
        return

    keyboard = []
    for i, c in enumerate(user_coops_list):
        label = f"{c['fee']} | {c['days']}gün | {c['time']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"koopcik_{i}")])
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="koop_iptal")])

    await update.message.reply_text(
        "🚪 *Hangi kooptan çıkmak istiyorsun?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# CALLBACK HANDLER (tüm buton tıklamaları)
# ──────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    d = query.data
    user_id = str(query.from_user.id)
    user_name = query.from_user.first_name

    # ── MOOD OYU ──────────────────────────────
    if d.startswith("mood_"):
        score = int(d.split("_")[1])
        data["mood_votes"][user_id] = score
        save_data(data)
        label = MOODS[str(score)]
        await query.edit_message_text(
            f"✅ Oyun kaydedildi: {label}\n\n"
            f"📊 Güncel Mood: {mood_average()}"
        )

    # ── KOOP: FEE SEÇİMİ ──────────────────────
    elif d.startswith("koop_fee_"):
        fee = d.replace("koop_fee_", "")
        context.user_data["koop_fee"] = fee
        keyboard = [
            [InlineKeyboardButton(f"📅 {day} Gün", callback_data=f"koop_day_{day}")]
            for day in DAYS
        ]
        keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="koop_geri_fee")])
        await query.edit_message_text(
            f"💼 *YENİ KOOPERATIF*\n\n"
            f"✅ Ücret: `{fee}`\n"
            f"Adım 2/3 — Gün sayısı seç:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # ── KOOP: GÜN SEÇİMİ ──────────────────────
    elif d.startswith("koop_day_"):
        days = int(d.replace("koop_day_", ""))
        fee = context.user_data.get("koop_fee", "?")
        context.user_data["koop_days"] = days
        keyboard = [
            [InlineKeyboardButton(t, callback_data=f"koop_time_{i}")]
            for i, t in enumerate(TIMES)
        ]
        keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="koop_geri_day")])
        await query.edit_message_text(
            f"💼 *YENİ KOOPERATIF*\n\n"
            f"✅ Ücret: `{fee}`\n"
            f"✅ Süre: `{days} gün`\n"
            f"Adım 3/3 — Zaman dilimi seç:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # ── KOOP: ZAMAN SEÇİMİ ────────────────────
    elif d.startswith("koop_time_"):
        time_idx = int(d.replace("koop_time_", ""))
        time_val = TIMES[time_idx]
        fee = context.user_data.get("koop_fee", "?")
        days = context.user_data.get("koop_days", 0)
        key = coop_key(fee, days, time_val)

        # Kural kontrolleri
        user_coops_list = data["coops"].get(user_id, [])

        # 4 koop limiti
        if len(user_coops_list) >= MAX_COOPS:
            await query.edit_message_text(
                f"❌ *Koop limitine ulaştın!*\n"
                f"Bir kişi en fazla {MAX_COOPS} koopa katılabilir.\n"
                f"Çıkmak için /koopcik komutunu kullan.",
                parse_mode="Markdown",
            )
            return

        # Aynı ücret + aynı gün kombinasyonu kontrolü
        duplicate = any(
            c["fee"] == fee and c["days"] == days for c in user_coops_list
        )
        if duplicate:
            await query.edit_message_text(
                f"⚠️ *Zaten bu kombinasyonda bir koopun var!*\n\n"
                f"`{fee}` ücretiyle `{days} gün` koopa zaten katıldın.\n"
                f"Farklı gün sayısı veya farklı ücret seç.",
                parse_mode="Markdown",
            )
            return

        # Koopa ekle
        tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
        new_coop = {"fee": fee, "days": days, "time": time_val, "tarih": tarih}
        if user_id not in data["coops"]:
            data["coops"][user_id] = []
        data["coops"][user_id].append(new_coop)

        if key not in data["teams"]:
            data["teams"][key] = []
        if user_id not in data["teams"][key]:
            data["teams"][key].append(user_id)

        save_data(data)

        team_count = len(data["teams"][key])
        await query.edit_message_text(
            f"✅ *KOOPA KATILDIN!*\n\n"
            f"💰 Ücret: `{fee}`\n"
            f"📅 Süre:  `{days} gün`\n"
            f"🕐 Zaman: {time_val}\n"
            f"👥 Takım: {team_count} kişi\n\n"
            f"📌 Koop ID: `{key}`\n"
            f"📋 Kooplarını görmek için /koopum yaz.",
            parse_mode="Markdown",
        )

    # ── KOOP'TAN ÇIK ──────────────────────────
    elif d.startswith("koopcik_"):
        idx = int(d.replace("koopcik_", ""))
        user_coops_list = data["coops"].get(user_id, [])
        if idx >= len(user_coops_list):
            await query.edit_message_text("❌ Geçersiz seçim.")
            return

        removed = user_coops_list.pop(idx)
        data["coops"][user_id] = user_coops_list
        key = coop_key(removed["fee"], removed["days"], removed["time"])
        if key in data["teams"] and user_id in data["teams"][key]:
            data["teams"][key].remove(user_id)
            if not data["teams"][key]:
                del data["teams"][key]

        save_data(data)
        await query.edit_message_text(
            f"✅ *Kooptan çıkıldı:*\n"
            f"`{removed['fee']}` — {removed['days']} gün — {removed['time']}"
            , parse_mode="Markdown",
        )

    # ── GERİ BUTONLARI ─────────────────────────
    elif d == "koop_geri_fee":
        keyboard = [
            [InlineKeyboardButton(f"💰 {fee}", callback_data=f"koop_fee_{fee}")]
            for fee in FEES
        ]
        keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="koop_iptal")])
        await query.edit_message_text(
            "💼 *YENİ KOOPERATIF*\n\nAdım 1/3 — Ücret seç:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif d == "koop_geri_day":
        fee = context.user_data.get("koop_fee", "?")
        keyboard = [
            [InlineKeyboardButton(f"📅 {day} Gün", callback_data=f"koop_day_{day}")]
            for day in DAYS
        ]
        keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="koop_geri_fee")])
        await query.edit_message_text(
            f"💼 *YENİ KOOPERATIF*\n\n✅ Ücret: `{fee}`\nAdım 2/3 — Gün sayısı seç:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # ── İPTAL ──────────────────────────────────
    elif d == "koop_iptal":
        context.user_data.clear()
        await query.edit_message_text("❌ İşlem iptal edildi.")


# ──────────────────────────────────────────────
# UYGULAMA BAŞLATMA
# ──────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Komutlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CommandHandler("mood", mood))
    app.add_handler(CommandHandler("moodsonuc", mood_sonuc))
    app.add_handler(CommandHandler("koop", koop_baslat))
    app.add_handler(CommandHandler("kooplistesi", koop_listesi))
    app.add_handler(CommandHandler("koopum", koopum))
    app.add_handler(CommandHandler("koopcik", koop_cik))

    # Callback (buton tıklamaları)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Üye giriş/çıkış takibi (chat_member güncellemeleri)
    app.add_handler(
        ChatMemberHandler(track_chat_members, ChatMemberHandler.CHAT_MEMBER)
    )

    print("🤖 Bot başlatılıyor...")
    app.run_polling(allowed_updates=["message", "callback_query", "chat_member"])


if __name__ == "__main__":
    main()
