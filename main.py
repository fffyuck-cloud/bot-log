#==============================================================
#          🤖 DISCORD LOG BOT - PYTHON FINAL v6
#   ✅ Đã XÓA log thành viên vào/ra (welcome bot lo rồi)
#   ✅ Fix bot.run sai vị trí + thiếu EMBED_COLOR
#   ✅ Menu dropdown + FULL tin nhắn/ảnh/gif/link/file
#==============================================================
import discord
from discord import app_commands
from discord.ext import commands
import json, os, re, traceback
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

#==============================================================
# ⚙️ CONFIG — Token lấy từ biến môi trường (KHÔNG ghi trong code)
#==============================================================
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = int(os.environ.get("GUILD_ID", "0"))
EMBED_COLOR = 0x000000   # Màu đen
THUMBNAIL = "https://i.pinimg.com/736x/e5/0f/53/e50f5361e265e7d22731829b7bc5d7a0.jpg"

if not TOKEN:
    raise SystemExit(
        "❌ Chưa có token!\n"
        "   Đặt biến môi trường DISCORD_TOKEN trước khi chạy:\n"
        "   Windows:  setx DISCORD_TOKEN \"dán_token_here\"\n"
        "   Render:   Environment → Add Environment Variable"
    )

#==============================================================
# 💾 LƯU CÀI ĐẶT
#==============================================================
SETTINGS_FILE = "settings.json"
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_log_channel(guild, log_type):
    cid = load_settings().get(str(guild.id), {}).get(log_type)
    return guild.get_channel(int(cid)) if cid else None

def set_log_channel(guild_id, log_type, channel_id):
    data = load_settings()
    data.setdefault(str(guild_id), {})[log_type] = str(channel_id)
    save_settings(data)

#==============================================================
# 🛠️ HÀM HỖ TRỢ
#==============================================================
URL_REGEX = re.compile(r"(https?://[^\s]+)")
IMG_URL_REGEX = re.compile(r"^https?://[^\s]+\.(png|jpe?g|gif|webp|bmp)(\?.*)?$", re.I)

def chunk(text, size):
    if not text:
        return [""]
    return [text[i:i+size] for i in range(0, len(text), size)]

def base_embed(title, image_url=None):
    e = discord.Embed(title=title, color=EMBED_COLOR)
    e.set_image(url=image_url or THUMBNAIL)
    e.set_footer(text="Log System")
    e.timestamp = discord.utils.utcnow()
    return e

def sanitize(text):
    if not text:
        return "(trống)"
    return text.replace("```", "``\u200b`")

def user_info(user):
    return f"> 👤 **Người dùng:** {user.mention} `{user}`\n"

def now_r():
    return f"<t:{int(discord.utils.utcnow().timestamp())}:R>"

#==============================================================
# 🤖 KHỞI TẠO BOT
#==============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

#==============================================================
# 📨 LOG TIN NHẮN — FULL mọi loại
#==============================================================
@bot.event
async def on_message(message):
    try:
        if message.author.bot or not message.guild:
            return

        log_channel = get_log_channel(message.guild, "messageLog")
        if not log_channel:
            return

        user = message.author
        avatar = user.display_avatar.url
        info = (user_info(user) +
                f"> 📍 **Kênh:** {message.channel.mention} `#{message.channel.name}`\n"
                f"> ⏰ **Thời gian:** <t:{int(message.created_at.timestamp())}:R>\n\n")

        reply_info = ""
        if message.reference and message.reference.resolved:
            reply_info = f"> ↩️ **Trả lời:** {message.reference.resolved.author.mention}\n\n"

        gif_files = [a for a in message.attachments if a.content_type == "image/gif"]
        img_files = [a for a in message.attachments if a.content_type and
                     a.content_type.startswith("image/") and a.content_type != "image/gif"]
        direct_img = IMG_URL_REGEX.match(message.content)
        other_files = [a for a in message.attachments
                       if not a.content_type or not a.content_type.startswith("image/")]
        links = URL_REGEX.findall(message.content)
        text = URL_REGEX.sub("", message.content).strip()

        # 🎬 GIF
        if gif_files:
            e = base_embed("🎬 GIF MỚI", image_url=gif_files[0].url)
            e.set_author(name=f"GIF Log • {user}", icon_url=avatar)
            e.description = (info + f"**Số lượng GIF:** `{len(gif_files)}`\n" +
                             "\n".join(f"`{i+1}.` `{g.filename}` • `{g.size/1024:.1f} KB`"
                                       for i, g in enumerate(gif_files)))
            embeds = [e]
            for g in gif_files[1:]:
                e2 = discord.Embed(color=EMBED_COLOR)
                e2.set_image(url=g.url)
                embeds.append(e2)
            for i in range(0, len(embeds), 10):
                await log_channel.send(embeds=embeds[i:i+10])

        # 🖼️ ẢNH
        if img_files or direct_img:
            entries = []
            if direct_img:
                entries.append((direct_img.group(0), "Link ảnh", None, None))
            for a in img_files:
                entries.append((a.url, a.filename, a.width, a.height))
            listing = ""
            for i, (url, name, w, h) in enumerate(entries):
                if w:
                    listing += f"`{i+1}.` `{name}` • `{w}x{h}` • [Xem]({url})\n"
                else:
                    listing += f"`{i+1}.` {name}: {url}\n"
            e = base_embed("🖼️ ẢNH MỚI", image_url=entries[0][0])
            e.set_author(name=f"Image Log • {user}", icon_url=avatar)
            e.description = info + f"**Số lượng ảnh:** `{len(entries)}`\n{listing}"
            embeds = [e]
            for url, *_ in entries[1:]:
                e2 = discord.Embed(color=EMBED_COLOR)
                e2.set_image(url=url)
                embeds.append(e2)
            for i in range(0, len(embeds), 10):
                await log_channel.send(embeds=embeds[i:i+10])

        # 🔗 LINK
        if links and not direct_img:
            header = (info + reply_info +
                      f"**Số lượng link:** `{len(links)}`\n\n**Danh sách đầy đủ:**\n")
            body = "\n".join(f"`{i+1}.` {l}" for i, l in enumerate(links))
            parts = chunk(sanitize(header + body), 4000)
            for idx, part in enumerate(parts):
                e = base_embed("🔗 LINK MỚI" if idx == 0 else f"🔗 LINK (phần {idx+1})")
                e.set_author(name=f"Link Log • {user}", icon_url=avatar)
                e.description = part
                await log_channel.send(embed=e)

        # 📁 FILE
        if other_files:
            header = info + f"**Số lượng file:** `{len(other_files)}`\n\n**Chi tiết:**\n"
            body = "\n".join(
                f"`{i+1}.` **{f.filename}**\n> 📦 `{f.size/1024:.2f} KB` • [⬇️ Tải xuống]({f.url})"
                for i, f in enumerate(other_files))
            parts = chunk(sanitize(header + body), 4000)
            for idx, part in enumerate(parts):
                e = base_embed("📁 FILE MỚI" if idx == 0 else f"📁 FILE (phần {idx+1})")
                e.set_author(name=f"File Log • {user}", icon_url=avatar)
                e.description = part
                await log_channel.send(embed=e)

        # 💬 CHAT
        if text:
            full = sanitize(text)
            header = info + reply_info + "**Nội dung:**\n"
            parts = chunk(full, 3700)
            for idx, part in enumerate(parts):
                e = base_embed("💬 TIN NHẮN MỚI" if idx == 0 else f"💬 TIN NHẮN (phần {idx+1})")
                e.set_author(name=f"Chat Log • {user}", icon_url=avatar)
                if idx == 0:
                    sticker = ""
                    if message.stickers:
                        sticker = "\n\n> 🎭 **Sticker:** " + ", ".join(
                            f"`{s.name}`" for s in message.stickers)
                    e.description = header + f"```\n{part}\n```" + sticker
                    e.add_field(name="🆔 Message ID", value=f"`{message.id}`", inline=True)
                    e.add_field(name="🆔 User ID", value=f"`{user.id}`", inline=True)
                else:
                    e.description = f"```\n{part}\n```"
                await log_channel.send(embed=e)
    except Exception:
        print("❌ LỖI on_message:")
        traceback.print_exc()

#==============================================================
# 🗑️ XÓA TIN
#==============================================================
@bot.event
async def on_message_delete(message):
    try:
        if not message.guild:
            return
        if message.author and message.author.bot:
            return
        log_channel = get_log_channel(message.guild, "messageLog")
        if not log_channel:
            return

        first_img = message.attachments[0].url if message.attachments else THUMBNAIL
        e = base_embed("🗑️ TIN NHẮN BỊ XÓA", image_url=first_img)
        if message.author:
            e.set_author(name=f"Delete Log • {message.author}",
                         icon_url=message.author.display_avatar.url)
            user_line = user_info(message.author)
        else:
            user_line = "> 👤 **Người dùng:** `Không rõ`\n"
        attach = ("\n".join(f"> `{a.filename}` → [Xem]({a.url})" for a in message.attachments)
                  if message.attachments else "> Không có")
        content_parts = chunk(sanitize(message.content), 3500)
        e.description = (user_line +
                         f"> 📍 **Kênh:** {message.channel.mention} `#{message.channel.name}`\n"
                         f"> ⏰ **Xóa lúc:** {now_r()}\n\n"
                         f"**Nội dung đã xóa:**\n```\n{content_parts[0]}\n```\n"
                         f"**Đính kèm ({len(message.attachments)} file):**\n{attach}")
        if message.author:
            e.add_field(name="🆔 Message ID", value=f"`{message.id}`", inline=True)
            e.add_field(name="🆔 User ID", value=f"`{message.author.id}`", inline=True)
        embeds = [e]
        for i, part in enumerate(content_parts[1:], start=2):
            e2 = base_embed(f"🗑️ NỘI DUNG XÓA (phần {i})")
            e2.description = f"```\n{part}\n```"
            embeds.append(e2)
        for a in message.attachments[1:]:
            e2 = discord.Embed(color=EMBED_COLOR)
            e2.set_image(url=a.url)
            embeds.append(e2)
        for i in range(0, len(embeds), 10):
            await log_channel.send(embeds=embeds[i:i+10])
    except Exception:
        print("❌ LỖI on_message_delete:")
        traceback.print_exc()

#==============================================================
# ✏️ SỬA TIN
#==============================================================
@bot.event
async def on_message_edit(before, after):
    try:
        if not before.guild or (before.author and before.author.bot):
            return
        if before.content == after.content:
            return
        log_channel = get_log_channel(before.guild, "messageLog")
        if not log_channel:
            return
        user = before.author
        old_parts = chunk(sanitize(before.content), 1800)
        new_parts = chunk(sanitize(after.content), 1800)
        for i in range(max(len(old_parts), len(new_parts))):
            old_p = old_parts[i] if i < len(old_parts) else "(...)"
            new_p = new_parts[i] if i < len(new_parts) else "(...)"
            e = base_embed("✏️ TIN NHẮN ĐƯỢC SỬA" if i == 0 else f"✏️ SỬA TIN (phần {i+1})")
            e.set_author(name=f"Edit Log • {user}", icon_url=user.display_avatar.url)
            e.description = (
                (user_info(user) +
                 f"> 📍 **Kênh:** {before.channel.mention} `#{before.channel.name}`\n"
                 f"> ⏰ **Sửa lúc:** {now_r()}\n\n" if i == 0 else "") +
                f"**❌ Nội dung cũ:**\n```\n{old_p}\n```\n"
                f"**✅ Nội dung mới:**\n```\n{new_p}\n```")
            if i == 0:
                e.add_field(name="🔗 Jump to message",
                            value=f"[Bấm vào đây]({after.jump_url})", inline=True)
            await log_channel.send(embed=e)
    except Exception:
        print("❌ LỖI on_message_edit:")
        traceback.print_exc()

#==============================================================
# ❌ ĐÃ XÓA: log thành viên vào (welcome bot lo rồi)
# ❌ ĐÃ XÓA: log thành viên rời (goodbye bot lo rồi)
#==============================================================

#==============================================================
# 🔨 BAN / UNBAN
#==============================================================
@bot.event
async def on_member_ban(guild, user):
    try:
        log_channel = get_log_channel(guild, "serverLog")
        if not log_channel:
            return
        e = base_embed("🔨 THÀNH VIÊN BỊ BAN", image_url=user.display_avatar.url)
        e.set_author(name=f"Ban Log • {user}", icon_url=user.display_avatar.url)
        e.description = user_info(user) + f"> ⏰ **Ban lúc:** {now_r()}\n> 🆔 User ID: `{user.id}`"
        await log_channel.send(embed=e)
    except Exception:
        traceback.print_exc()

@bot.event
async def on_member_unban(guild, user):
    try:
        log_channel = get_log_channel(guild, "serverLog")
        if not log_channel:
            return
        e = base_embed("🔓 THÀNH VIÊN ĐƯỢC UNBAN", image_url=user.display_avatar.url)
        e.set_author(name=f"Unban Log • {user}", icon_url=user.display_avatar.url)
        e.description = user_info(user) + f"> ⏰ **Unban lúc:** {now_r()}\n> 🆔 User ID: `{user.id}`"
        await log_channel.send(embed=e)
    except Exception:
        traceback.print_exc()

#==============================================================
# 🎙️ VOICE
#==============================================================
@bot.event
async def on_voice_state_update(member, before, after):
    try:
        log_channel = get_log_channel(member.guild, "voiceLog")
        if not log_channel:
            return
        avatar = member.display_avatar.url
        if before.channel is None and after.channel is not None:
            e = base_embed("🎙️ VÀO VOICE CHANNEL")
            e.set_author(name=f"Voice Log • {member}", icon_url=avatar)
            e.description = user_info(member) + f"> 🔊 **Kênh:** `{after.channel.name}`\n> ⏰ **Thời gian:** {now_r()}"
            await log_channel.send(embed=e)
        elif before.channel is not None and after.channel is None:
            e = base_embed("🔇 RỜI VOICE CHANNEL")
            e.set_author(name=f"Voice Log • {member}", icon_url=avatar)
            e.description = user_info(member) + f"> 🔊 **Kênh:** `{before.channel.name}`\n> ⏰ **Thời gian:** {now_r()}"
            await log_channel.send(embed=e)
        elif before.channel != after.channel and after.channel is not None:
            e = base_embed("↔️ CHUYỂN VOICE CHANNEL")
            e.set_author(name=f"Voice Log • {member}", icon_url=avatar)
            e.description = (user_info(member) +
                             f"> 🔊 **Từ:** `{before.channel.name}`\n"
                             f"> 📍 **Đến:** `{after.channel.name}`\n"
                             f"> ⏰ **Thời gian:** {now_r()}")
            await log_channel.send(embed=e)
    except Exception:
        traceback.print_exc()

#==============================================================
# 📢 KÊNH + 🎭 ROLE
#==============================================================
@bot.event
async def on_guild_channel_create(channel):
    try:
        log_channel = get_log_channel(channel.guild, "serverLog")
        if not log_channel:
            return
        e = base_embed("📢 KÊNH MỚI ĐƯỢC TẠO")
        e.description = (f"> 📍 **Tên kênh:** {channel.mention} `{channel.name}`\n"
                         f"> 📂 **Loại:** `{channel.type}`\n"
                         f"> 🆔 Channel ID: `{channel.id}`\n"
                         f"> ⏰ **Thời gian:** {now_r()}")
        await log_channel.send(embed=e)
    except Exception:
        traceback.print_exc()

@bot.event
async def on_guild_channel_delete(channel):
    try:
        log_channel = get_log_channel(channel.guild, "serverLog")
        if not log_channel:
            return
        e = base_embed("🗑️ KÊNH BỊ XÓA")
        e.description = (f"> 📍 **Tên kênh:** `#{channel.name}`\n"
                         f"> 🆔 Channel ID: `{channel.id}`\n"
                         f"> ⏰ **Thời gian:** {now_r()}")
        await log_channel.send(embed=e)
    except Exception:
        traceback.print_exc()

@bot.event
async def on_guild_role_create(role):
    try:
        log_channel = get_log_channel(role.guild, "serverLog")
        if not log_channel:
            return
        e = base_embed("🎭 ROLE MỚI ĐƯỢC TẠO")
        e.description = (f"> 🎭 **Role:** {role.mention} `{role.name}`\n"
                         f"> 🎨 **Màu:** `{role.color}`\n"
                         f"> 🆔 Role ID: `{role.id}`\n"
                         f"> ⏰ **Thời gian:** {now_r()}")
        await log_channel.send(embed=e)
    except Exception:
        traceback.print_exc()

@bot.event
async def on_guild_role_delete(role):
    try:
        log_channel = get_log_channel(role.guild, "serverLog")
        if not log_channel:
            return
        e = base_embed("❌ ROLE BỊ XÓA")
        e.description = (f"> 🎭 **Role:** `@{role.name}`\n"
                         f"> 🆔 Role ID: `{role.id}`\n"
                         f"> ⏰ **Thời gian:** {now_r()}")
        await log_channel.send(embed=e)
    except Exception:
        traceback.print_exc()

#==============================================================
# ⌨️ MENU /log — 4 lựa chọn (đã bỏ "Log Thành viên")
#==============================================================
class ChannelPick(discord.ui.ChannelSelect):
    def __init__(self, log_type, label):
        super().__init__(placeholder="📍 Chọn kênh log...",
                         channel_types=[discord.ChannelType.text])
        self.log_type = log_type
        self.label = label

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            channel = interaction.guild.get_channel(self.values[0].id)
            if channel is None:
                await interaction.followup.send("❌ Không tìm thấy kênh này!", ephemeral=True)
                return
            perms = channel.permissions_for(interaction.guild.me)
            if not (perms.send_messages and perms.embed_links):
                await interaction.followup.send(
                    f"❌ Bot thiếu quyền **Gửi tin nhắn / Nhúng liên kết** trong {channel.mention}!",
                    ephemeral=True)
                return
            set_log_channel(interaction.guild_id, self.log_type, channel.id)
            e = discord.Embed(title="✅ CÀI ĐẶT THÀNH CÔNG", color=EMBED_COLOR)
            e.description = (f"> 📋 **Loại log:** `{self.label}`\n"
                             f"> 📍 **Kênh:** {channel.mention} `#{channel.name}`\n"
                             f"> 👤 **Cài bởi:** {interaction.user.mention}")
            await interaction.followup.send(embed=e, ephemeral=True)
        except Exception:
            traceback.print_exc()
            try:
                await interaction.followup.send("❌ Có lỗi, xem log để biết chi tiết!", ephemeral=True)
            except:
                pass

class LogMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(
        placeholder="🔽 Chọn loại log cần cài...",
        options=[
            discord.SelectOption(label="Log Tin nhắn", value="messageLog", emoji="💬",
                                 description="Chat • Ảnh • GIF • Link • File • Embed"),
            discord.SelectOption(label="Log Server", value="serverLog", emoji="🖥️",
                                 description="Ban • Unban • Kênh • Role"),
            discord.SelectOption(label="Log Voice", value="voiceLog", emoji="🎙️",
                                 description="Vào / Ra / Chuyển kênh thoại"),
            discord.SelectOption(label="Xem cài đặt hiện tại", value="view", emoji="⚙️",
                                 description="Xem toàn bộ kênh log đã cài"),
        ]
    )
    async def select_menu(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            await interaction.response.defer(ephemeral=True)
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("❌ Chỉ admin mới dùng được!", ephemeral=True)
                return
            choice = select.values[0]

            if choice == "view":
                settings = load_settings().get(str(interaction.guild_id), {})
                def get_ch(key):
                    cid = settings.get(key)
                    if not cid:
                        return "`❌ Chưa cài`"
                    ch = interaction.guild.get_channel(int(cid))
                    return f"{ch.mention} `#{ch.name}`" if ch else "`❌ Kênh không tồn tại`"
                e = discord.Embed(title="⚙️ CÀI ĐẶT LOG SERVER", color=EMBED_COLOR)
                e.description = (f"> 💬 **Tin nhắn:** {get_ch('messageLog')}\n"
                                 f"> 🖥️ **Server:** {get_ch('serverLog')}\n"
                                 f"> 🎙️ **Voice:** {get_ch('voiceLog')}")
                await interaction.followup.send(embed=e, ephemeral=True)
                return

            labels = {"messageLog": "TIN NHẮN", "serverLog": "SERVER", "voiceLog": "VOICE"}
            view = discord.ui.View(timeout=120)
            view.add_item(ChannelPick(choice, labels[choice]))
            await interaction.followup.send(
                f"📍 Đang cài: **Log {labels[choice]}** — chọn kênh bên dưới:",
                view=view, ephemeral=True)
        except Exception:
            traceback.print_exc()
            try:
                await interaction.followup.send("❌ Có lỗi, xem log để biết chi tiết!", ephemeral=True)
            except:
                pass

@bot.tree.command(name="log", description="⚙️ Mở menu cài đặt kênh log")
async def log_command(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Chỉ admin mới dùng được lệnh này!", ephemeral=True)
            return
        e = discord.Embed(title="⚙️ CÀI ĐẶT LOG", color=EMBED_COLOR)
        e.description = "🔽 **Chọn loại log** từ menu bên dưới:"
        await interaction.response.send_message(embed=e, view=LogMenuView(), ephemeral=True)
    except Exception:
        traceback.print_exc()

#==============================================================
# 📖 /help — BẢNG FULL LỆNH
#==============================================================
@bot.tree.command(name="help", description="📖 Bảng đầy đủ lệnh và loại log")
async def help_command(interaction: discord.Interaction):
    try:
        e = discord.Embed(title="📖 BẢNG LỆNH & LOẠI LOG", color=EMBED_COLOR)
        e.add_field(name="⌨️ LỆNH BOT", value=(
            "> `/log` — Menu cài đặt kênh log (dropdown)\n"
            "> `/help` — Bảng lệnh này\n"
            "> `/ping` — Kiểm tra độ trễ bot"), inline=False)
        e.add_field(name="💬 LOG TIN NHẮN", value=(
            "> 💬 Chat (FULL) • 🖼️ Ảnh (TO) • 🎬 GIF (TO)\n"
            "> 🔗 Link (FULL) • 📁 File • 📋 Embed\n"
            "> 🗑️ Xóa tin • ✏️ Sửa tin"), inline=False)
        e.add_field(name="🖥️ LOG SERVER", value=(
            "> 🔨 Ban • 🔓 Unban\n"
            "> 📢 Tạo kênh • 🗑️ Xóa kênh\n"
            "> 🎭 Tạo role • ❌ Xóa role"), inline=False)
        e.add_field(name="🎙️ LOG VOICE", value=(
            "> 🎙️ Vào • 🔇 Rời • ↔️ Chuyển kênh"), inline=False)
        e.set_footer(text="Log System • Dùng /log để cài kênh")
        e.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=e, ephemeral=True)
    except Exception:
        traceback.print_exc()

@bot.tree.command(name="ping", description="📡 Kiểm tra độ trễ bot")
async def ping(interaction: discord.Interaction):
    try:
        e = discord.Embed(title="🏓 PONG!", color=EMBED_COLOR)
        e.description = f"> 💓 **API Latency:** `{round(bot.latency*1000)}ms`"
        await interaction.response.send_message(embed=e, ephemeral=True)
    except Exception:
        traceback.print_exc()

#==============================================================
# ✅ on_ready — SYNC LỆNH
#==============================================================
@bot.event
async def on_ready():
    print("═══════════════════════════════════")
    print(f"🤖 Đăng nhập: {bot.user}")
    print(f"🌐 Servers: {len(bot.guilds)}")
    print("═══════════════════════════════════")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="📝 Log hệ thống"),
        status=discord.Status.online)
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Sync NGAY {len(synced)} lệnh vào server {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            print(f"✅ Sync global {len(synced)} lệnh (chờ vài phút tới 1 tiếng)")
    except Exception:
        print("❌ LỖI SYNC:")
        traceback.print_exc()

#==============================================================
# 🌐 GIỮ PORT CHO RENDER (HTTP server giả — chạy ngầm)
#==============================================================
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, *args):
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    print(f"🌐 Keep-alive server chạy ở port {port}")
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

#================== CHẠY BOT (DUY NHẤT — ở cuối file) ==================
bot.run(TOKEN)
