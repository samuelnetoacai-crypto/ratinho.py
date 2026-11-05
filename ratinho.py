from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import os
import json
import random
import time

# Parte pra manter online
app = Flask('')

@app.route('/')
def home():
    return "Ratinho ta online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===== SISTEMA DE VOLTS =====
ARQUIVO = "volts.json"

def carregar():
    if not os.path.exists(ARQUIVO):
        return {}
    try:
        with open(ARQUIVO, "r") as f:
            return json.load(f)
    except:
        return {}

def salvar(dados):
    with open(ARQUIVO, "w") as f:
        json.dump(dados, f, indent=4)

def get_volts(user_id):
    dados = carregar()
    return dados.get(str(user_id), {}).get("volts", 0)

def set_volts(user_id, valor):
    dados = carregar()
    uid = str(user_id)
    if uid not in dados:
        dados[uid] = {"volts": 0, "last_daily": 0}
    dados[uid]["volts"] = valor
    salvar(dados)

def add_volts(user_id, valor):
    dados = carregar()
    uid = str(user_id)
    if uid not in dados:
        dados[uid] = {"volts": 0, "last_daily": 0}
    dados[uid]["volts"] += valor
    salvar(dados)
    return dados[uid]["volts"]

# Botões de aceitar / recusar o pagamento
class ConfirmarPagamento(discord.ui.View):
    def __init__(self, pagador, recebedor, valor):
        super().__init__(timeout=60)
        self.pagador = pagador
        self.recebedor = recebedor
        self.valor = valor
        self.resultado = None

    @discord.ui.button(label="✅ Aceitar", style=discord.ButtonStyle.green)
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.recebedor.id:
            await interaction.response.send_message("Só quem vai receber pode aceitar!", ephemeral=True)
            return
        self.resultado = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.red)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.recebedor.id:
            await interaction.response.send_message("Só quem vai receber pode recusar!", ephemeral=True)
            return
        self.resultado = False
        self.stop()
        await interaction.response.defer()

# Parte do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="v", intents=intents)

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.CustomActivity(
            name=f"Atualmente estou em {len(bot.guilds)} servidores!"
        )
    )

@bot.event
async def on_guild_join(guild):
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.CustomActivity(
            name=f"Atualmente estou em {len(bot.guilds)} servidores!"
        )
    )

@bot.event
async def on_guild_remove(guild):
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.CustomActivity(
            name=f"Atualmente estou em {len(bot.guilds)} servidores!"
        )
    )

# ===== COMANDOS DE VOLTS =====

@bot.command(name="atm")
async def atm(ctx, membro: discord.Member = None):
    if membro is None:
        membro = ctx.author
    saldo = get_volts(membro.id)
    await ctx.send(f"🏦 **ATM do {membro.display_name}**\n⚡ **{saldo} volts**")

@bot.group(name="volts", invoke_without_command=True)
async def volts_group(ctx):
    await ctx.send("Use: `v volts pagar @pessoa 100`")

@volts_group.command(name="pagar")
async def volts_pagar(ctx, membro: discord.Member, valor: int):
    if membro.id == ctx.author.id:
        await ctx.send("Você não pode pagar pra você mesmo!")
        return
    if valor <= 0:
        await ctx.send("O valor tem que ser maior que 0!")
        return

    saldo = get_volts(ctx.author.id)
    if saldo < valor:
        await ctx.send(f"Você só tem ⚡ **{saldo} volts**, não dá pra pagar ⚡ **{valor} volts**!")
        return

    view = ConfirmarPagamento(ctx.author, membro, valor)
    msg = await ctx.send(
        f"{membro.mention}, o {ctx.author.mention} quer te pagar ⚡ **{valor} volts**!\nVocê aceita? (60 segundos)",
        view=view
    )
    await view.wait()

    if view.resultado is None:
        await msg.edit(content="⏰ Tempo acabou! Pagamento cancelado.", view=None)
        return
    if view.resultado is False:
        await msg.edit(content="❌ Pagamento recusado!", view=None)
        return

    # Aceitou - faz a transferência
    add_volts(ctx.author.id, -valor)
    add_volts(membro.id, valor)
    await msg.edit(
        content=f"✅ **Pagamento confirmado!**\n{ctx.author.mention} pagou ⚡ **{valor} volts** para {membro.mention}!",
        view=None
    )

@bot.command(name="daily")
async def daily(ctx):
    dados = carregar()
    uid = str(ctx.author.id)
    agora = time.time()

    if uid not in dados:
        dados[uid] = {"volts": 0, "last_daily": 0}

    ultimo = dados[uid].get("last_daily", 0)
    falta = 86400 - (agora - ultimo)

    if falta > 0:
        horas = int(falta // 3600)
        minutos = int((falta % 3600) // 60)
        await ctx.send(f"⏰ Você já pegou seu daily! Volta em **{horas}h {minutos}min**.")
        return

    ganho = random.randint(2000, 5000)
    dados[uid]["volts"] += ganho
    dados[uid]["last_daily"] = agora
    salvar(dados)
    await ctx.send(f"🎉 **DAILY!** Você ganhou ⚡ **{ganho} volts**!\nSeu saldo agora é ⚡ **{dados[uid]['volts']} volts**.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user.mentioned_in(message):
        await message.channel.send(f"**Oiê {message.author.mention}! Eu sou o Ratinho e meu prefixo é v**")
    await bot.process_commands(message)

keep_alive()
bot.run(os.getenv("TOKEN"))
