import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

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

# Criar pasta de logs se não existir
Path("logs").mkdir(exist_ok=True)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

@bot.command()
async def track(ctx, user: discord.Member, channel: discord.TextChannel):
    """Escolhe o usuário e canal a ser rastreado"""
    global tracked_user, tracked_channel, user_message_count, log_file_path
    tracked_user = user
    tracked_channel = channel
    user_message_count[user.id] = 0

    # Nome do arquivo de log com o nick
    log_file_path = f"logs/{user.name}.txt"

    # Contar mensagens antigas
    count = 0
    async for msg in channel.history(limit=None):
        if msg.author.id == user.id:
            count += 1
            salvar_log(msg)

    user_message_count[user.id] = count

    await ctx.send(f"📊 Agora rastreando {user.mention} em {channel.mention}. Mensagens antigas: **{count}**")
    print(f"[LOG] {user} já tinha {count} mensagens no canal {channel}")

def salvar_log(message):
    """Salva mensagem no arquivo de log"""
    global log_file_path
    if log_file_path:
        with open(log_file_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message.author}: {message.content}\n")

@bot.event
async def on_message(message):
    global tracked_user, tracked_channel, user_message_count

    if tracked_user and tracked_channel:
        if message.channel.id == tracked_channel.id and message.author.id == tracked_user.id:
            user_message_count[tracked_user.id] += 1
            salvar_log(message)
            print(f"[LOG] {tracked_user} → {user_message_count[tracked_user.id]} mensagens")

    await bot.process_commands(message)

@bot.command()
async def count(ctx):
    """Mostra a contagem atual do usuário rastreado"""
    if tracked_user and tracked_user.id in user_message_count:
        await ctx.send(f"📈 {tracked_user.mention} já enviou **{user_message_count[tracked_user.id]}** mensagens em {tracked_channel.mention}")
    else:
        await ctx.send("⚠️ Nenhum usuário está sendo rastreado no momento.")

bot.run(TOKEN)
