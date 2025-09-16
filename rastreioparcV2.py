import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import re
import openpyxl

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
links_duplicados = []
admin_user = None
autopagamento = False  # controle para enviar valores em tempo real

# Valor pago por parceria
VALOR_POR_PARCERIA = 0.07

# Criar pastas de logs
Path("logs").mkdir(exist_ok=True)
Path("logs/relatorios").mkdir(exist_ok=True)

# Regex para detectar links do Discord
DISCORD_LINK_REGEX = r"(https?://(www\.)?(discord\.gg|discord(app)?\.com/invite)/[A-Za-z0-9]+)"

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

@bot.command()
async def track(ctx, user: discord.Member, channel: discord.TextChannel):
    """Escolhe o usuário e canal a ser rastreado"""
    global tracked_user, tracked_channel, user_message_count, log_file_path, log_links_path, links_encontrados, links_duplicados, admin_user
    tracked_user = user
    tracked_channel = channel
    user_message_count[user.id] = 0
    links_encontrados = {}
    links_duplicados = []
    admin_user = ctx.author

    log_file_path = f"logs/{user.name}_mensagens.txt"
    log_links_path = f"logs/{user.name}_links.txt"

    count = 0
    async for msg in channel.history(limit=None):
        if msg.author.id == user.id:
            count += 1
            salvar_log(msg)
            await verificar_links(msg)

    user_message_count[user.id] = count

    await ctx.send(f"📊 Agora rastreando {user.mention} em {channel.mention}. Mensagens antigas: **{count}**")
    print(f"[LOG] {user} já tinha {count} mensagens no canal {channel}")

def salvar_log(message):
    """Salva mensagem no arquivo geral"""
    if log_file_path:
        with open(log_file_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message.author}: {message.content}\n")

async def verificar_links(message):
    """Procura links do Discord e registra duplicados sem apagar"""
    global links_encontrados, links_duplicados, admin_user, autopagamento
    links = re.findall(DISCORD_LINK_REGEX, message.content)

    if links:
        for link_tuple in links:
            link = link_tuple[0]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if link not in links_encontrados:
                links_encontrados[link] = 1
                print(f"[LINK] Novo link encontrado: {link}")

                # Auto pagamento em tempo real
                if autopagamento and admin_user:
                    valor = len(links_encontrados) * VALOR_POR_PARCERIA
                    try:
                        await admin_user.send(
                            f"💰 Nova parceria registrada!\n"
                            f"🔗 {link}\n"
                            f"📅 {timestamp}\n"
                            f"💵 Total acumulado: R${valor:.2f}"
                        )
                    except:
                        print("⚠️ Não consegui mandar mensagem para o admin.")
            else:
                links_encontrados[link] += 1
                links_duplicados.append((link, message.jump_url, timestamp))
                print(f"[LINK] Link duplicado {links_encontrados[link]}x → {link}")

                if admin_user:
                    try:
                        await admin_user.send(
                            f"⚠️ Mensagem DUPLICADA detectada!\n"
                            f"👤 Usuário: {message.author}\n"
                            f"🔗 Link: {link}\n"
                            f"📅 Data: {timestamp}\n"
                            f"🔗 Mensagem: {message.jump_url}"
                        )
                    except:
                        print("⚠️ Não foi possível enviar DM ao admin.")

@bot.event
async def on_message(message):
    global tracked_user, tracked_channel, user_message_count

    if tracked_user and tracked_channel:
        if message.channel.id == tracked_channel.id and message.author.id == tracked_user.id:
            user_message_count[tracked_user.id] += 1
            salvar_log(message)
            await verificar_links(message)
            print(f"[LOG] {tracked_user} → {user_message_count[tracked_user.id]} mensagens")

    await bot.process_commands(message)

@bot.command()
async def count(ctx):
    """Mostra a contagem atual"""
    if tracked_user and tracked_user.id in user_message_count:
        total_unicos = len(links_encontrados)
        total_duplicados = len(links_duplicados)
        total_geral = total_unicos + total_duplicados

        await ctx.send(
            f"📈 {tracked_user.mention} já enviou **{user_message_count[tracked_user.id]}** mensagens em {tracked_channel.mention}\n"
            f"🔗 Links únicos: **{total_unicos}**\n"
            f"♻️ Links duplicados encontrados: **{total_duplicados}**\n"
            f"📊 Total de links detectados: **{total_geral}**"
        )
    else:
        await ctx.send("⚠️ Nenhum usuário está sendo rastreado.")

@bot.command()
async def pagamento(ctx):
    """Calcula o pagamento"""
    if tracked_user and links_encontrados:
        total_unicos = len(links_encontrados)
        total_duplicados = len(links_duplicados)
        valor = total_unicos * VALOR_POR_PARCERIA

        resposta = (
            f"💰 {tracked_user.mention} fez **{total_unicos} parcerias únicas**.\n"
            f"♻️ Foram detectados **{total_duplicados} links duplicados**.\n"
            f"Pagamento devido: **R${valor:.2f}**"
        )

        await ctx.send(resposta)
    else:
        await ctx.send("⚠️ Nenhum usuário está sendo rastreado ou nenhum link foi encontrado.")

@bot.command()
async def duplicados(ctx):
    """Lista todos os duplicados"""
    if tracked_user and links_duplicados:
        resposta = f"📑 Relatório de duplicados de {tracked_user.mention}:\n\n"
        blocos = []
        for i, dup in enumerate(links_duplicados, start=1):
            linha = f"{i}. {dup[0]} → [Mensagem]({dup[1]}) em {dup[2]}"
            blocos.append(linha)

        for i in range(0, len(blocos), 15):
            parte = "\n".join(blocos[i:i+15])
            await ctx.send(parte)
    else:
        await ctx.send("✅ Nenhum duplicado encontrado.")

@bot.command()
async def relatorio(ctx):
    """Exporta relatório em Excel"""
    if not tracked_user:
        await ctx.send("⚠️ Nenhum usuário rastreado.")
        return

    nome_arquivo = f"logs/relatorios/{tracked_user.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Relatório"

    ws.append(["Data", "Usuário", "Link", "Tipo", "Mensagem URL"])

    # Links únicos
    for link, qtd in links_encontrados.items():
        ws.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tracked_user.name, link, "Único", "—"])

    # Links duplicados
    for link, url, data in links_duplicados:
        ws.append([data, tracked_user.name, link, "Duplicado", url])

    wb.save(nome_arquivo)
    await ctx.send(f"📂 Relatório exportado: `{nome_arquivo}`")

@bot.command()
async def autopagamento(ctx, modo: str):
    """Liga ou desliga atualização automática de pagamento"""
    global autopagamento
    if modo.lower() == "on":
        autopagamento = True
        await ctx.send("✅ Auto pagamento ativado! O admin receberá atualizações no privado.")
    elif modo.lower() == "off":
        autopagamento = False
        await ctx.send("❌ Auto pagamento desativado.")
    else:
        await ctx.send("⚠️ Use: `!autopagamento on` ou `!autopagamento off`")

bot.run(TOKEN)
