import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import re

# Carregar TOKEN do arquivo .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("❌ ERRO: Token não encontrado! Verifique se o arquivo .env existe e tem DISCORD_TOKEN=SEU_TOKEN")

# Ativar intents necessárias
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Variáveis globais
user_message_count = {}
tracked_user = None
tracked_channel = None
log_file_path = None
log_links_path = None
links_encontrados = {}

# Criar pasta de logs se não existir
Path("logs").mkdir(exist_ok=True)

# Regex para detectar links do Discord
DISCORD_LINK_REGEX = r"(https?://(www\.)?(discord\.gg|discord(app)?\.com/invite)/[A-Za-z0-9]+)"

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

@bot.command()
async def track(ctx, user: discord.Member, channel: discord.TextChannel):
    """Escolhe o usuário e canal a ser rastreado"""
    global tracked_user, tracked_channel, user_message_count, log_file_path, log_links_path, links_encontrados
    tracked_user = user
    tracked_channel = channel
    user_message_count[user.id] = 0
    links_encontrados = {}

    # Nome dos arquivos de log
    log_file_path = f"logs/{user.name}_mensagens.txt"
    log_links_path = f"logs/{user.name}_links.txt"

    # Contar mensagens antigas
    count = 0
    async for msg in channel.history(limit=None):
        if msg.author.id == user.id:
            count += 1
            salvar_log(msg)
            verificar_links(msg)

    user_message_count[user.id] = count

    await ctx.send(f"📊 Agora rastreando {user.mention} em {channel.mention}. Mensagens antigas: **{count}**")
    print(f"[LOG] {user} já tinha {count} mensagens no canal {channel}")

def salvar_log(message):
    """Salva mensagem no arquivo geral"""
    global log_file_path
    if log_file_path:
        with open(log_file_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message.author}: {message.content}\n")

def verificar_links(message):
    """Procura links do Discord e salva em log específico"""
    global log_links_path, links_encontrados
    links = re.findall(DISCORD_LINK_REGEX, message.content)

    if links and log_links_path:
        with open(log_links_path, "a", encoding="utf-8") as f:
            for link_tuple in links:
                link = link_tuple[0]  # O regex retorna grupos, pegamos só a URL
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if link not in links_encontrados:
                    links_encontrados[link] = 1
                    f.write(f"[{timestamp}] NOVO link: {link}\n")
                    print(f"[LINK] Novo link encontrado: {link}")
                else:
                    links_encontrados[link] += 1
                    f.write(f"[{timestamp}] REPOSTADO ({links_encontrados[link]}x): {link}\n")
                    print(f"[LINK] Link repetido {links_encontrados[link]}x → {link}")

@bot.event
async def on_message(message):
    global tracked_user, tracked_channel, user_message_count

    if tracked_user and tracked_channel:
        if message.channel.id == tracked_channel.id and message.author.id == tracked_user.id:
            user_message_count[tracked_user.id] += 1
            salvar_log(message)
            verificar_links(message)
            print(f"[LOG] {tracked_user} → {user_message_count[tracked_user.id]} mensagens")

    await bot.process_commands(message)

@bot.command()
async def count(ctx):
    """Mostra a contagem atual do usuário rastreado"""
    if tracked_user and tracked_user.id in user_message_count:
        await ctx.send(
            f"📈 {tracked_user.mention} já enviou **{user_message_count[tracked_user.id]}** mensagens em {tracked_channel.mention}\n"
            f"🔗 Links únicos: **{len(links_encontrados)}** | Total de links: **{sum(links_encontrados.values())}**"
        )
    else:
        await ctx.send("⚠️ Nenhum usuário está sendo rastreado no momento.")

bot.run(TOKEN)
