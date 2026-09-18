#==============================================================
#   🤖 DISCORD LOG BOT - LITE v7 (TIẾT KIỆM RAM)
#   Log: Chat | Ảnh | GIF | Link | File | Voice | Ban | Kênh | Role
#   ❌ Không log member vào/ra (welcome bot lo rồi)
#   ⚡ Tối ưu: cache RAM, không cache member, Client thuần
#==============================================================
import discord
from discord import app_commands, MemberCacheFlags
import json, os, re, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

#==============================================================
# ⚙️ CONFIG
#==============================================================
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = int(os.environ.get("GUILD_ID", "0"))
COLOR = 0x000000
THUMB = "https://i.pinimg.com/736x/e5/0f/53/e50f5361e265e7d22731829b7bc5d7a0.jpg"

if not TOKEN:
    raise SystemExit("❌ Thiếu biến môi trường DISCORD_TOKEN!")

#==============================================================
# 💾 SETTINGS — cache trong RAM, chỉ ghi disk khi CÀI ĐẶT MỚI
#   (bản cũ đọc file settings.json ở MỖI tin nhắn = tốn RAM/CPU)
#==============================================================
try:
    with open("settings.json", "r", encoding="utf-8") as f:
        _S = json.load(f)
except Exception:
    _S = {}

def get_ch(guild, key):
    cid = _S.get(str(guild.id), {}).get(key)
    return guild.get_channel(int(cid)) if cid else None

def set_ch(gid, key, cid):
    _S.setdefault(str(gid), {})[key] = str(cid)
    try:
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(_S, f)
    except Exception:
        pass

#==============================================================
# ⚡ REGEX — compile 1 lần duy nhất lúc khởi động
#==============================================================
URL = re.compile(r"https?://\S+")
IMG_URL = re.compile(r"^https?://\S+\.(?:png|jpe?g|gif|webp|bmp)(\?.*)?$", re.I)

#==============================================================
# ⚡ CLIENT THUẦN + KHÔNG CACHE MEMBER
#   - Client nhẹ hơn commands.Bot (bỏ khung lệnh prefix không dùng)
#   - MemberCacheFlags.none() = không lưu member trong RAM (tiết kiệm MẠNH)
#   - Đã bỏ members intent (vì không log join/leave nữa)
#==============================================================
intents = discord.Intents.default()
intents.message_content = True   # bắt buộc để đọc nội dung log chat
intents.voice_states = True      # log voice

class LogBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents, member_cache_flags=MemberCacheFlags.none())
        self.tree = app_commands.CommandTree(self)

client = LogBot()

#==============================================================
# 🛠️ HÀM NHỎ GỌN
#==============================================================
def embed(title, img=None):
    e = discord.Embed(title=title, color=COLOR)
    e.set_image(url=img or THUMB)
    e.set_footer(text="Log System")
    return e

def clean(t):
    return t.replace("```", "``\u200b`") if t else "(trống)"

def part(t, n):
    return [t[i:i+n] for i in range(0, len(t), n)] or [""]

async def send_log(guild, key, embeds):
    """Gửi list embed vào kênh log (tự chia 10 embed/tin)"""
    ch = get_ch(guild, key)
    if ch:
        for i in range(0, len(embeds), 10):
            await ch.send(embeds=embeds[i:i+10])

#==============================================================
# 📨 LOG TIN NHẮN
#==============================================================
@client.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    ch = get_ch(message.guild, "messageLog")
    if not ch:
        return

    user = message.author
    avatar = user.display_avatar.url
    info = (f"> 👤 **Người dùng:** {user.mention} `{user}`\n"
            f"> 📍 **Kênh:** {message.channel.mention} `#{message.channel.name}`\n"
            f"> ⏰ <t:{int(message.created_at.timestamp())}:R>\n\n")

    reply = ""
    if message.reference and message.reference.resolved:
        reply = f"> ↩️ **Trả lời:** {message.reference.resolved.author.mention}\n\n"

    gifs = [a for a in message.attachments if a.content_type == "image/gif"]
    imgs = [a for a in message.attachments if a.content_type and
            a.content_type.startswith("image/") and a.content_type != "image/gif"]
    direct = IMG_URL.match(message.content or "")
    files = [a for a in message.attachments
             if not a.content_type or not a.content_type.startswith("image/")]
    links = URL.findall(message.content)
    text = URL.sub("", message.content or "").strip()

    try:
        # 🎬 GIF
        if gifs:
            e = embed("🎬 GIF MỚI", gifs[0].url)
            e.set_author(name=f"GIF Log • {user}", icon_url=avatar)
            e.description = info + f"**Số lượng:** `{len(gifs)}`"
            es = [e] + [discord.Embed(color=COLOR).set_image(url=g.url) for g in gifs[1:]]
            await send_log(message.guild, "messageLog", es)

        # 🖼️ ẢNH
        if imgs or direct:
            first = direct.group(0) if direct else imgs[0].url
            e = embed("🖼️ ẢNH MỚI", first)
            e.set_author(name=f"Image Log • {user}", icon_url=avatar)
            e.description = info + f"**Số lượng ảnh:** `{len(imgs) + (1 if direct else 0)}`"
            es = [e] + [discord.Embed(color=COLOR).set_image(url=a.url) for a in imgs[1:]]
            await send_log(message.guild, "messageLog", es)

        # 🔗 LINK
        if links and not direct:
            body = info + reply + f"**Số lượng link:** `{len(links)}`\n\n" + \
                   "\n".join(f"`{i+1}.` {l}" for i, l in enumerate(links))
            for idx, p in enumerate(part(clean(body), 4000)):
                e = embed("🔗 LINK MỚI" if not idx else f"🔗 LINK ({idx+1})")
                e.set_author(name=f"Link Log • {user}", icon_url=avatar)
                e.description = p
                await ch.send(embed=e)

        # 📁 FILE
        if files:
            body = info + f"**Số lượng file:** `{len(files)}`\n\n" + "\n".join(
                f"`{i+1}.` **{f.filename}** • `{f.size/1024:.1f} KB` • [Tải]({f.url})"
                for i, f in enumerate(files))
            for idx, p in enumerate(part(clean(body), 4000)):
                e = embed("📁 FILE MỚI" if not idx else f"📁 FILE ({idx+1})")
                e.set_author(name=f"File Log • {user}", icon_url=avatar)
                e.description = p
                await ch.send(embed=e)

        # 💬 CHAT — FULL
        if text:
            body = info + reply + "**Nội dung:**\n"
            for idx, p in enumerate(part(clean(text), 3600)):
                e = embed("💬 TIN NHẮN MỚI" if not idx else f"💬 TIN NHẮN ({idx+1})")
                e.set_author(name=f"Chat Log • {user}", icon_url=avatar)
                e.description = body + f"```\n{p}\n```" if not idx else f"```\n{p}\n```"
                await ch.send(embed=e)
    except Exception:
        pass  # Lite: không spam log lỗi

#==============================================================
# 🗑️ XÓA TIN
#==============================================================
@client.event
async def on_message_delete(message):
    if not message.guild or (message.author and message.author.bot):
        return
    ch = get_ch(message.guild, "messageLog")
    if not ch:
        return
    try:
        img = message.attachments[0].url if message.attachments else THUMB
        e = embed("🗑️ TIN NHẮN BỊ XÓA", img)
        if message.author:
            e.set_author(name=f"Delete • {message.author}",
                         icon_url=message.author.display_avatar.url)
            who = f"> 👤 {message.author.mention} `{message.author}`\n"
        else:
            who = "> 👤 `Không rõ`\n"
        attach = ("\n".join(f"> `{a.filename}`" for a in message.attachments)
                  if message.attachments else "> Không có")
        parts = part(clean(message.content), 3400)
        e.description = (who +
                         f"> 📍 {message.channel.mention} `#{message.channel.name}`\n\n"
                         f"**Đã xóa:**\n```\n{parts[0]}\n```\n**File:**\n{attach}")
        es = [e]
        for p in parts[1:]:
            e2 = embed("🗑️ (tiếp)")
            e2.description = f"```\n{p}\n```"
            es.append(e2)
        for a in message.attachments[1:]:
            es.append(discord.Embed(color=COLOR).set_image(url=a.url))
        await send_log(message.guild, "messageLog", es)
    except Exception:
        pass

#==============================================================
# ✏️ SỬA TIN
#==============================================================
@client.event
async def on_message_edit(before, after):
    if not before.guild or (before.author and before.author.bot):
        return
    if before.content == after.content:
        return
    ch = get_ch(before.guild, "messageLog")
    if not ch:
        return
    try:
        user = before.author
        e = embed("✏️ TIN NHẮN ĐƯỢC SỬA")
        e.set_author(name=f"Edit • {user}", icon_url=user.display_avatar.url)
        e.description = (f"> 👤 {user.mention} `{user}`\n"
                         f"> 📍 {before.channel.mention}\n\n"
                         f"**❌ Cũ:**\n```\n{clean(before.content)[:1800]}\n```\n"
                         f"**✅ Mới:**\n```\n{clean(after.content)[:1800]}\n```\n"
                         f"🔗 [Xem tin]({after.jump_url})")
        await ch.send(embed=e)
    except Exception:
        pass

#==============================================================
# 🔨 BAN / UNBAN
#==============================================================
@client.event
async def on_member_ban(guild, user):
    ch = get_ch(guild, "serverLog")
    if not ch:
        return
    e = embed("🔨 BỊ BAN", user.display_avatar.url)
    e.set_author(name=f"Ban • {user}", icon_url=user.display_avatar.url)
    e.description = f"> 👤 {user.mention} `{user}`\n> 🆔 `{user.id}`"
    await ch.send(embed=e)

@client.event
async def on_member_unban(guild, user):
    ch = get_ch(guild, "serverLog")
    if not ch:
        return
    e = embed("🔓 ĐƯỢC UNBAN", user.display_avatar.url)
    e.set_author(name=f"Unban • {user}", icon_url=user.display_avatar.url)
    e.description = f"> 👤 {user.mention} `{user}`\n> 🆔 `{user.id}`"
    await ch.send(embed=e)

#==============================================================
# 🎙️ VOICE
#==============================================================
@client.event
async def on_voice_state_update(member, before, after):
    ch = get_ch(member.guild, "voiceLog")
    if not ch:
        return
    try:
        if not before.channel and after.channel:
            t, desc = "🎙️ VÀO VOICE", f"> 🔊 `{after.channel.name}`"
        elif before.channel and not after.channel:
            t, desc = "🔇 RỜI VOICE", f"> 🔊 `{before.channel.name}`"
        elif before.channel != after.channel and after.channel:
            t, desc = "↔️ CHUYỂN VOICE", (f"> Từ `{before.channel.name}`\n> Đến `{after.channel.name}`")
        else:
            return
        e = embed(t)
        e.set_author(name=f"Voice • {member}", icon_url=member.display_avatar.url)
        e.description = f"> 👤 {member.mention}\n{desc}"
        await ch.send(embed=e)
    except Exception:
        pass

#==============================================================
# 📢 KÊNH + 🎭 ROLE
#==============================================================
@client.event
async def on_guild_channel_create(c):
    ch = get_ch(c.guild, "serverLog")
    if ch:
        e = embed("📢 TẠO KÊNH")
        e.description = f"> {c.mention} `#{c.name}`"
        await ch.send(embed=e)

@client.event
async def on_guild_channel_delete(c):
    ch = get_ch(c.guild, "serverLog")
    if ch:
        e = embed("🗑️ XÓA KÊNH")
        e.description = f"> `#{c.name}`"
        await ch.send(embed=e)

@client.event
async def on_guild_role_create(r):
    ch = get_ch(r.guild, "serverLog")
    if ch:
        e = embed("🎭 TẠO ROLE")
        e.description = f"> {r.mention} `{r.name}`"
        await ch.send(embed=e)

@client.event
async def on_guild_role_delete(r):
    ch = get_ch(r.guild, "serverLog")
    if ch:
        e = embed("❌ XÓA ROLE")
        e.description = f"> `@{r.name}`"
        await ch.send(embed=e)

#==============================================================
# ⌨️ MENU /log (dropdown 4 lựa chọn)
#==============================================================
class ChannelPick(discord.ui.ChannelSelect):
    def __init__(self, key, label):
        super().__init__(placeholder="📍 Chọn kênh log...",
                         channel_types=[discord.ChannelType.text])
        self.key, self.label = key, label

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.guild.get_channel(self.values[0].id)
        if not channel:
            return
        set_ch(interaction.guild_id, self.key, channel.id)
        e = embed("✅ CÀI ĐẶT THÀNH CÔNG")
        e.description = (f"> Loại: `{self.label}`\n"
                         f"> Kênh: {channel.mention}\n"
                         f"> Bởi: {interaction.user.mention}")
        await interaction.followup.send(embed=e, ephemeral=True)

class LogMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.select(placeholder="🔽 Chọn loại log...",
        options=[
            discord.SelectOption(label="Log Tin nhắn", value="messageLog", emoji="💬",
                                 description="Chat • Ảnh • GIF • Link • File"),
            discord.SelectOption(label="Log Server", value="serverLog", emoji="🖥️",
                                 description="Ban • Kênh • Role"),
            discord.SelectOption(label="Log Voice", value="voiceLog", emoji="🎙️",
                                 description="Vào / Rời / Chuyển kênh"),
            discord.SelectOption(label="Xem cài đặt", value="view", emoji="⚙️",
                                 description="Xem kênh log đã cài"),
        ])
    async def select_menu(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return
        choice = select.values[0]

        if choice == "view":
            s = _S.get(str(interaction.guild_id), {})
            def g(k):
                c = interaction.guild.get_channel(int(s[k])) if s.get(k) else None
                return f"{c.mention}" if c else "`❌ Chưa cài`"
            e = embed("⚙️ CÀI ĐẶT HIỆN TẠI")
            e.description = (f"> 💬 Tin nhắn: {g('messageLog')}\n"
                             f"> 🖥️ Server: {g('serverLog')}\n"
                             f"> 🎙️ Voice: {g('voiceLog')}")
            await interaction.followup.send(embed=e, ephemeral=True)
            return

        labels = {"messageLog": "TIN NHẮN", "serverLog": "SERVER", "voiceLog": "VOICE"}
        v = discord.ui.View(timeout=120)
        v.add_item(ChannelPick(choice, labels[choice]))
        await interaction.followup.send(
            f"📍 **Log {labels[choice]}** — chọn kênh:", view=v, ephemeral=True)

@client.tree.command(name="log", description="⚙️ Cài đặt kênh log")
async def log_cmd(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Chỉ admin!", ephemeral=True)
    e = embed("⚙️ CÀI ĐẶT LOG")
    e.description = "🔽 Chọn loại log:"
    await interaction.response.send_message(embed=e, view=LogMenu(), ephemeral=True)

@client.tree.command(name="help", description="📖 Bảng lệnh")
async def help_cmd(interaction: discord.Interaction):
    e = embed("📖 LỆNH & LOG")
    e.description = (
        "**⌨️ Lệnh:** `/log` • `/help` • `/ping`\n\n"
        "**💬 Tin nhắn:** Chat FULL • Ảnh/GIF TO • Link FULL • File • Xóa/Sửa tin\n\n"
        "**🖥️ Server:** Ban/Unban • Tạo/Xóa kênh • Tạo/Xóa role\n\n"
        "**🎙️ Voice:** Vào • Rời • Chuyển kênh")
    await interaction.response.send_message(embed=e, ephemeral=True)

@client.tree.command(name="ping", description="📡 Độ trễ bot")
async def ping_cmd(interaction: discord.Interaction):
    e = embed("🏓 PONG!")
    e.description = f"> 💓 `{round(client.latency*1000)}ms`"
    await interaction.response.send_message(embed=e, ephemeral=True)

#==============================================================
# ⚡ SYNC + STATUS
#==============================================================
async def sync_commands():
    try:
        if GUILD_ID:
            g = discord.Object(id=GUILD_ID)
            client.tree.copy_global_to(guild=g)
            synced = await client.tree.sync(guild=g)
            print(f"✅ Sync NGAY {len(synced)} lệnh vào server {GUILD_ID}")
        else:
            synced = await client.tree.sync()
            print(f"✅ Sync global {len(synced)} lệnh")
    except Exception as err:
        print(f"❌ Lỗi sync: {err}")

@client.event
async def setup_hook():
    await sync_commands()

@client.event
async def on_ready():
    print("═══════════════════════")
    print(f"🤖 {client.user} | 🌐 {len(client.guilds)} server")
    print("═══════════════════════")
    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="Log hệ thống"))

#==============================================================
# 🌐 KEEP-ALIVE CHO RENDER (chạy ngầm, gần như tốn 0 RAM)
#==============================================================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *a):
        pass

def keepalive():
    try:
        HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000)), ), Handler).serve_forever()
    except Exception:
        pass

threading.Thread(target=keepalive, daemon=True).start()

#================== CHẠY ==================
client.run(TOKEN)
