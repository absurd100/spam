from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from database import get_my_admin_groups, update_config, get_config

# --- SIMULASI DATA (Ganti dengan Database Anda) ---
admin_groups = [
    {"id": -100123456789, "title": "Grup A"},
    {"id": -100987654321, "title": "Grup B"}
]

@Client.on_message(filters.command("start") & filters.private)
async def start_private(client, message):
    me = await client.get_me()
    add_url = f"t.me/{me.username}?startgroup=true&admin=delete_messages"

    # Teks yang Anda minta
    text = (
        "<b>╔══════════════════════════╗</b>\n"
        "<b>║      🛡️ BOT ANTISPAM      ║</b>\n"
        "<b>╚══════════════════════════╝</b>\n\n"
        "Sistem mitigasi spam massal lintas grup secara <b>real-time</b>.\n\n"
        "<b>📖 CARA PENGGUNAAN:</b>\n"
        "① Klik tombol di bawah → tambahkan ke grup.\n"
        "② Berikan izin <b>Administrator + Hapus Pesan</b>. Untuk mengaktifkan CAS, berikan ijin blokir pengguna pada bot jika diperlukan.\n"
        "③ Bot langsung aktif memantau secara otomatis."
    )

    # Keyboard dengan tombol tambahan Admin Group Menu
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Aktifkan Proteksi di Grup", url=add_url)],
        [InlineKeyboardButton("⚙️ Admin Group Menu", callback_data="admin_menu")]
    ])

    await message.reply(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@Client.on_callback_query(filters.regex("start"))
async def back_to_start(client, callback):
    await callback.message.delete() # Menghapus menu admin
    await start_private(client, callback.message) # Menampilkan ulang menu start

# --- Handler Admin Menu & Pengaturan ---

@Client.on_callback_query(filters.regex("admin_menu"))
async def admin_menu_handler(client, callback):
    await callback.answer("Memuat daftar grup...")
    groups = await get_my_admin_groups(client, callback.from_user.id)
    if not groups:
        await callback.message.edit("❌ Anda tidak menjadi admin di grup mana pun.")
        return
    buttons = [[InlineKeyboardButton(g['title'], callback_data=f"manage_{g['id']}")] for g in groups]
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="start")])
    await callback.message.edit("<b>Pilih grup untuk diatur:</b>", reply_markup=InlineKeyboardMarkup(buttons))

# 1. Perbaiki manage_group_settings agar lebih tangguh
@Client.on_callback_query(filters.regex(r"manage_(-?\d+)"))
async def manage_group_settings(client, callback):
    # Mengambil ID dari callback data yang benar (format: manage_ID)
    chat_id = int(callback.data.split("_")[1])
    cfg = await get_config(chat_id)

    local_txt = "✅ ON" if cfg.get("local") else "❌ OFF"
    global_txt = "✅ ON" if cfg.get("global") else "❌ OFF"
    waktu = cfg.get("expiry", 3600) // 60

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Local: {local_txt}", callback_data=f"toggle_local_{chat_id}"), InlineKeyboardButton("🔄 Toggle", callback_data=f"toggle_local_{chat_id}")],
        [InlineKeyboardButton(f"Global: {global_txt}", callback_data=f"toggle_global_{chat_id}"), InlineKeyboardButton("🔄 Toggle", callback_data=f"toggle_global_{chat_id}")],
        [InlineKeyboardButton(f"Waktu: {waktu}m", callback_data="none"), InlineKeyboardButton(" ➖", callback_data=f"time_dec_{chat_id}"), InlineKeyboardButton("➕", callback_data=f"time_inc_{chat_id}")],
        [InlineKeyboardButton("✅ Whitelist CAS", callback_data=f"wl_cas_{chat_id}"), InlineKeyboardButton("❌ Un-Whitelist", callback_data=f"unwl_cas_{chat_id}")],
        [InlineKeyboardButton("🔙 Kembali ke Daftar Grup", callback_data="admin_menu")]
    ])

    # Update pesan dengan data baru
    await callback.message.edit(f"<b>Pengaturan Grup ID:</b> <code>{chat_id}</code>", reply_markup=keyboard)

# 2. Perbaiki handle_toggle
@Client.on_callback_query(filters.regex(r"toggle_(local|global)_(-?\d+)"))
async def handle_toggle(client, callback):
    parts = callback.data.split("_")
    key = parts[1]
    chat_id = int(parts[2])

    # Update ke database
    cfg = await get_config(chat_id)
    new_val = not cfg.get(key)
    await update_config(chat_id, key, new_val)

    # KUNCI: Kita buat callback data palsu agar manage_group_settings tidak error
    callback.data = f"manage_{chat_id}"
    await manage_group_settings(client, callback)

# 3. Perbaiki handle_time
@Client.on_callback_query(filters.regex(r"time_(inc|dec)_(-?\d+)"))
async def handle_time(client, callback):
    parts = callback.data.split("_")
    action = parts[1]
    chat_id = int(parts[2])

    cfg = await get_config(chat_id)
    current_expiry = cfg.get("expiry", 3600)
    new_expiry = (current_expiry + 3600) if action == "inc" else max(3600, current_expiry - 3600)

    await update_config(chat_id, "expiry", new_expiry)

    # KUNCI: Reset callback data ke format yang dikenal manage_group_settings
    callback.data = f"manage_{chat_id}"
    await manage_group_settings(client, callback)

@Client.on_callback_query(filters.regex(r"(wl|unwl)_cas_(-?\d+)"))
async def handle_wl_request(client, callback):
    # Logika sederhana: kirim pesan instruksi
    action = "Whitelist" if "wl_" in callback.data else "Unwhitelist"
    await callback.message.edit(f"Silakan kirim <b>ID User</b> untuk di-{action} (Ketik ID di kolom chat).")
    # Catatan: Untuk menangkap balasan ID user, diperlukan handler tambahan (FSM).

@Client.on_callback_query(filters.regex("admin_menu"))
async def admin_menu_handler(client, callback):
    await callback.answer("Memuat daftar grup...")
    groups = await get_my_admin_groups(client, callback.from_user.id)

    if not groups:
        await callback.message.edit("❌ Anda tidak menjadi admin di grup mana pun.")
        return

    buttons = [[InlineKeyboardButton(g['title'], callback_data=f"manage_{g['id']}")] for g in groups]
    buttons.append([InlineKeyboardButton("🔙 Kembali", callback_data="start")])

    await callback.message.edit("<b>Pilih grup untuk diatur:</b>", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("wl_add|wl_del"))
async def handle_wl(client, callback: CallbackQuery):
    action = "Whitelist" if "add" in callback.data else "Unwhitelist"
    await callback.message.reply(f"Silakan masukkan ID user untuk di-{action} (Kirim ID saja):")
    # Logika untuk menangkap ID user selanjutnya bisa menggunakan FSM (Finite State Machine)
