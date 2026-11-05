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
COR_PRINCIPAL = 0xF1C40F
COR_SUCESSO = 0x2ECC71
COR_ERRO = 0xE74C3C
COR_INFO = 0x3498DB

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

    @discord.ui.button(label="Aceitar", style=discord.ButtonStyle.green, emoji="✅")
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.recebedor.id:
            await interaction.response.send_message("Apenas o destinatário pode aceitar esta transferência.", ephemeral=True)
            return
        self.resultado = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.red, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.recebedor.id:
            await interaction.response.send_message("Apenas o destinatário pode recusar esta transferência.", ephemeral=True)
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

    embed = discord.Embed(
        title="🏦 Banco Volts",
        description=f"Saldo atual de **{membro.display_name}**",
        color=COR_PRINCIPAL,
        timestamp=ctx.message.created_at
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name="⚡ Volts", value=f"**{saldo:,}** volts".replace(",", "."), inline=False)
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.group(name="volts", invoke_without_command=True)
async def volts_group(ctx):
    embed = discord.Embed(
        title="⚡ Sistema Volts",
        description="Comandos disponíveis:",
        color=COR_INFO
    )
    embed.add_field(name="v volts pagar", value="`v volts pagar @usuário <valor>`\nRealiza uma transferência com confirmação.", inline=False)
    embed.add_field(name="v atm", value="`v atm` ou `v atm @usuário`\nConsulta o saldo de volts.", inline=False)
    embed.add_field(name="v daily", value="`v daily`\nResgata sua recompensa diária.", inline=False)
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@volts_group.command(name="pagar")
async def volts_pagar(ctx, membro: discord.Member = None, valor: int = None):
    if membro is None or valor is None:
        embed = discord.Embed(
            title="⚠️ Uso incorreto",
            description="Utilize o comando da seguinte forma:",
            color=COR_ERRO
        )
        embed.add_field(name="Formato", value="`v volts pagar @usuário <valor>`", inline=False)
        embed.add_field(name="Exemplo", value="`v volts pagar @Shy 500`", inline=False)
        await ctx.send(embed=embed)
        return

    if membro.id == ctx.author.id:
        embed = discord.Embed(
            title="⚠️ Transferência inválida",
            description="Você não pode realizar uma transferência para si mesmo.",
            color=COR_ERRO
        )
        await ctx.send(embed=embed)
        return

    if valor <= 0:
        embed = discord.Embed(
            title="⚠️ Valor inválido",
            description="O valor da transferência deve ser maior que zero.",
            color=COR_ERRO
        )
        await ctx.send(embed=embed)
        return

    saldo = get_volts(ctx.author.id)
    if saldo < valor:
        embed = discord.Embed(
            title="❌ Saldo insuficiente",
            description="Você não possui volts suficientes para concluir esta transferência.",
            color=COR_ERRO
        )
        embed.add_field(name="Seu saldo", value=f"⚡ **{saldo:,}** volts".replace(",", "."), inline=True)
        embed.add_field(name="Valor solicitado", value=f"⚡ **{valor:,}** volts".replace(",", "."), inline=True)
        await ctx.send(embed=embed)
        return

    view = ConfirmarPagamento(ctx.author, membro, valor)
    embed = discord.Embed(
        title="💸 Solicitação de Transferência",
        description=f"{membro.mention}, você recebeu uma solicitação de transferência.",
        color=COR_INFO
    )
    embed.add_field(name="Remetente", value=ctx.author.mention, inline=True)
    embed.add_field(name="Destinatário", value=membro.mention, inline=True)
    embed.add_field(name="Valor", value=f"⚡ **{valor:,}** volts".replace(",", "."), inline=False)
    embed.set_footer(text="Você possui 60 segundos para responder.")
    msg = await ctx.send(embed=embed, view=view)
    await view.wait()

    if view.resultado is None:
        embed_timeout = discord.Embed(
            title="⏰ Tempo esgotado",
            description="A solicitação de transferência expirou e foi cancelada automaticamente.",
            color=COR_ERRO
        )
        await msg.edit(embed=embed_timeout, view=None)
        return

    if view.resultado is False:
        embed_recusado = discord.Embed(
            title="❌ Transferência recusada",
            description=f"{membro.mention} recusou a transferência.",
            color=COR_ERRO
        )
        embed_recusado.add_field(name="Valor", value=f"⚡ **{valor:,}** volts".replace(",", "."), inline=False)
        await msg.edit(embed=embed_recusado, view=None)
        return

    add_volts(ctx.author.id, -valor)
    add_volts(membro.id, valor)
    novo_saldo_pagador = get_volts(ctx.author.id)
    novo_saldo_recebedor = get_volts(membro.id)

    embed_sucesso = discord.Embed(
        title="✅ Transferência concluída",
        description="A transferência foi confirmada com sucesso.",
        color=COR_SUCESSO
    )
    embed_sucesso.add_field(name="Remetente", value=f"{ctx.author.mention}\nSaldo atual: ⚡ **{novo_saldo_pagador:,}** volts".replace(",", "."), inline=True)
    embed_sucesso.add_field(name="Destinatário", value=f"{membro.mention}\nSaldo atual: ⚡ **{novo_saldo_recebedor:,}** volts".replace(",", "."), inline=True)
    embed_sucesso.add_field(name="Valor transferido", value=f"⚡ **{valor:,}** volts".replace(",", "."), inline=False)
    await msg.edit(embed=embed_sucesso, view=None)

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
        embed = discord.Embed(
            title="⏰ Recompensa diária indisponível",
            description="Você já resgatou sua recompensa diária.",
            color=COR_ERRO
        )
        embed.add_field(name="Próximo resgate em", value=f"**{horas}h {minutos}min**", inline=False)
        embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        return

    ganho = random.randint(2000, 5000)
    dados[uid]["volts"] += ganho
    dados[uid]["last_daily"] = agora
    salvar(dados)

    embed = discord.Embed(
        title="🎉 Recompensa Diária Resgatada",
        description=f"Parabéns, {ctx.author.mention}!",
        color=COR_SUCESSO
    )
    embed.add_field(name="Valor recebido", value=f"⚡ **{ganho:,}** volts".replace(",", "."), inline=True)
    embed.add_field(name="Saldo atual", value=f"⚡ **{dados[uid]['volts']:,}** volts".replace(",", "."), inline=True)
    embed.add_field(name="Próximo resgate", value="Disponível em 24 horas.", inline=False)
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user.mentioned_in(message):
        embed = discord.Embed(
            title="👋 Olá!",
            description=f"{message.author.mention}, eu sou o **Ratinho**.",
            color=COR_PRINCIPAL
        )
        embed.add_field(name="Prefixo", value="`v`", inline=False)
        embed.add_field(name="Exemplo", value="`v atm` • `v daily` • `v volts pagar @usuário 100`", inline=False)
        await message.channel.send(embed=embed)
    await bot.process_commands(message)

keep_alive()
bot.run(os.getenv("TOKEN"))
