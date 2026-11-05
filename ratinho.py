# ============================================================
#  RATINHO - BOT COMPLETO
#  1. Flask / Keep Alive
#  2. Banco de Dados (Volts + Config)
#  3. Helpers / Cores / Formatação
#  4. Views: Pagamento / Configurar / Ticket
#  5. Eventos (Logs / Entrada / Saída)
#  6. Comandos (Volts / Configurar / Embed)
# ============================================================

from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import random
import time
import re
import urllib.request
import urllib.parse
import asyncio

# ============================================================
#  1. FLASK - MANTER ONLINE
# ============================================================
app = Flask('')

@app.route('/')
def home():
    return "Ratinho ta online!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

# ============================================================
#  2. CONFIGS GERAIS + BANCO
# ============================================================
ARQUIVO = "volts.json"
ARQUIVO_CONFIG = "config.json"

COR_PRINCIPAL = 0xF1C40F  # Amarelo
COR_SUCESSO  = 0x2ECC71  # Verde
COR_ERRO     = 0xE74C3C  # Vermelho
COR_INFO     = 0x3498DB  # Azul

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

# ---------- Volts ----------
def carregar():
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        if not os.path.exists(ARQUIVO):
            return {}
        try:
            with open(ARQUIVO, "r") as f:
                return json.load(f)
        except:
            return {}
    try:
        req = urllib.request.Request(
            f"{UPSTASH_URL}/get/volts_db",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            return json.loads(data["result"]) if data.get("result") else {}
    except Exception as e:
        print(f"Erro ao carregar do Upstash: {e}")
        return {}

def salvar(dados):
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        with open(ARQUIVO, "w") as f:
            json.dump(dados, f, indent=4)
        return
    try:
        valor = json.dumps(dados)
        req = urllib.request.Request(
            f"{UPSTASH_URL}/set/volts_db/{urllib.parse.quote(valor)}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Erro ao salvar no Upstash: {e}")

# ---------- Config do Servidor ----------
def carregar_config():
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        if not os.path.exists(ARQUIVO_CONFIG):
            return {}
        try:
            with open(ARQUIVO_CONFIG, "r") as f:
                return json.load(f)
        except:
            return {}
    try:
        req = urllib.request.Request(
            f"{UPSTASH_URL}/get/config_db",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            return json.loads(data["result"]) if data.get("result") else {}
    except:
        return {}

def salvar_config(dados):
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        with open(ARQUIVO_CONFIG, "w") as f:
            json.dump(dados, f, indent=4)
        return
    try:
        valor = json.dumps(dados)
        req = urllib.request.Request(
            f"{UPSTASH_URL}/set/config_db/{urllib.parse.quote(valor)}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Erro ao salvar config: {e}")

def get_guild_config(guild_id):
    dados = carregar_config()
    gid = str(guild_id)
    if gid not in dados:
        dados[gid] = {
            "logs":    {"ativo": False, "canal": None},
            "ticket":  {"ativo": False, "canal_painel": None, "mensagem": "Clique no botão abaixo para abrir um ticket!\nNossa equipe vai te atender o mais rápido possível.", "cargo_suporte": None, "categoria": None},
            "entrada": {"ativo": False, "canal": None, "mensagem": "👋 {user} entrou em **{server}**!\nSeja bem-vindo(a)!"},
            "saida":   {"ativo": False, "canal": None, "mensagem": "🚪 {user} saiu de **{server}**.\nSentiremos sua falta!"},
        }
        salvar_config(dados)
    return dados[gid]

def update_guild_config(guild_id, nova):
    dados = carregar_config()
    dados[str(guild_id)] = nova
    salvar_config(dados)

# ============================================================
#  3. HELPERS
# ============================================================
def get_volts(user_id):
    return carregar().get(str(user_id), {}).get("volts", 0)

def add_volts(user_id, valor):
    dados = carregar()
    uid = str(user_id)
    if uid not in dados:
        dados[uid] = {"volts": 0, "last_daily": 0}
    dados[uid]["volts"] += valor
    salvar(dados)
    return dados[uid]["volts"]

def parse_cor(cor_str):
    if not cor_str:
        return COR_PRINCIPAL
    cor_str = cor_str.strip().lower()
    nomes = {
        "amarelo": 0xF1C40F, "vermelho": 0xE74C3C, "verde": 0x2ECC71, "azul": 0x3498DB,
        "roxo": 0x9B59B6, "rosa": 0xFF6B9D, "laranja": 0xE67E22, "preto": 0x2C3E50,
        "branco": 0xECF0F1, "cinza": 0x95A5A6, "ciano": 0x1ABC9C,
    }
    if cor_str in nomes:
        return nomes[cor_str]
    cor_str = cor_str.replace("#", "").replace("0x", "")
    try:
        return int(cor_str, 16)
    except:
        return COR_PRINCIPAL

def formatar_mensagem(texto, membro, guild):
    return (texto
        .replace("{user}", membro.mention)
        .replace("{usuario}", membro.mention)
        .replace("{nome}", membro.display_name)
        .replace("{server}", guild.name)
        .replace("{servidor}", guild.name)
        .replace("{membros}", str(guild.member_count)))

# --- Helpers de exibição (pra não ficar feio) ---
def status_txt(ativo: bool):
    return "🟢 Ativo" if ativo else "🔴 Desativado"

def canal_txt(canal_id):
    return f"<#{canal_id}>" if canal_id else "`Não definido`"

def cargo_txt(cargo_id):
    return f"<@&{cargo_id}>" if cargo_id else "`Não definido`"

def linha():
    return "────────────────────"

# ============================================================
#  4. VIEWS
# ============================================================
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

# ============================================================
#  BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="v", intents=intents)

# ============================================================
#  EMBEDS DO PAINEL CONFIGURAR - ORGANIZADOS
# ============================================================
def embed_painel_principal(guild, guild_id):
    cfg = get_guild_config(guild_id)
    e = discord.Embed(
        title="⚙️  Painel de Configuração",
        description="Configure as funções do Ratinho neste servidor.\nEscolha uma opção abaixo:",
        color=COR_PRINCIPAL
    )
    if guild.icon:
        e.set_thumbnail(url=guild.icon.url)
    e.add_field(
        name="📋  Events Logs",
        value=f"{status_txt(cfg['logs']['ativo'])}\n"
              f"**Canal:** {canal_txt(cfg['logs']['canal'])}\n"
              f"Registra mensagens, entradas, saídas, bans e mais.",
        inline=True
    )
    e.add_field(
        name="🎫  Ticket",
        value=f"{status_txt(cfg['ticket']['ativo'])}\n"
              f"**Painel:** {canal_txt(cfg['ticket']['canal_painel'])}\n"
              f"Sistema de atendimento por tickets.",
        inline=True
    )
    e.add_field(
        name="👋  Mensagem de Entradas",
        value=f"{status_txt(cfg['entrada']['ativo'])}\n"
              f"**Canal:** {canal_txt(cfg['entrada']['canal'])}\n"
              f"Boas-vindas quando alguém entra.",
        inline=True
    )
    e.add_field(
        name="🚪  Mensagem de Saídas",
        value=f"{status_txt(cfg['saida']['ativo'])}\n"
              f"**Canal:** {canal_txt(cfg['saida']['canal'])}\n"
              f"Despedida quando alguém sai.",
        inline=True
    )
    e.set_footer(text=f"{guild.name}  •  Painel de Configuração")
    return e

def embed_logs(guild_id):
    cfg = get_guild_config(guild_id)["logs"]
    e = discord.Embed(
        title="📋  Events Logs",
        description="Configure onde os logs do servidor vão aparecer.",
        color=COR_PRINCIPAL
    )
    e.add_field(name="Status", value=status_txt(cfg["ativo"]), inline=True)
    e.add_field(name="Canal", value=canal_txt(cfg["canal"]), inline=True)
    e.add_field(
        name="📌  O que é registrado",
        value="• Mensagem apagada / editada\n• Membro entrou / saiu\n• Membro banido / desbanido",
        inline=False
    )
    e.set_footer(text="Events Logs  •  Ratinho")
    return e

def embed_ticket(guild_id):
    cfg = get_guild_config(guild_id)["ticket"]
    e = discord.Embed(
        title="🎫  Ticket",
        description="Configure o sistema de tickets do servidor.",
        color=COR_PRINCIPAL
    )
    e.add_field(name="Status", value=status_txt(cfg["ativo"]), inline=True)
    e.add_field(name="Canal do Painel", value=canal_txt(cfg["canal_painel"]), inline=True)
    e.add_field(name="Cargo Suporte", value=cargo_txt(cfg["cargo_suporte"]), inline=True)
    e.add_field(name="Categoria", value=canal_txt(cfg["categoria"]), inline=True)
    e.add_field(name="💬  Mensagem do Painel", value=cfg["mensagem"][:1000], inline=False)
    e.set_footer(text="Ticket  •  Ratinho")
    return e

def embed_entrada_saida(guild_id, tipo):
    cfg = get_guild_config(guild_id)[tipo]
    is_entrada = tipo == "entrada"
    titulo = "👋  Mensagem de Entradas" if is_entrada else "🚪  Mensagem de Saídas"
    desc = "Configure a mensagem de boas-vindas." if is_entrada else "Configure a mensagem de despedida."
    e = discord.Embed(title=titulo, description=desc, color=COR_PRINCIPAL)
    e.add_field(name="Status", value=status_txt(cfg["ativo"]), inline=True)
    e.add_field(name="Canal", value=canal_txt(cfg["canal"]), inline=True)
    e.add_field(name="💬  Mensagem atual", value=cfg["mensagem"][:1000], inline=False)
    e.add_field(
        name="🔧  Variáveis disponíveis",
        value="`{user}`  •  menciona o membro\n`{nome}`  •  nome do membro\n`{server}`  •  nome do servidor\n`{membros}`  •  total de membros",
        inline=False
    )
    e.set_footer(text=f"{titulo}  •  Ratinho")
    return e

# ---------- Modals ----------
class ModalMensagem(discord.ui.Modal):
    def __init__(self, guild_id, tipo, titulo):
        super().__init__(title=titulo)
        self.guild_id = guild_id
        self.tipo = tipo
        cfg = get_guild_config(guild_id)
        atual = cfg["ticket"]["mensagem"] if tipo == "ticket_mensagem" else cfg[tipo]["mensagem"]
        self.msg = discord.ui.TextInput(
            label="Mensagem", style=discord.TextStyle.paragraph,
            placeholder="Digite a mensagem...", default=atual,
            max_length=1500, required=True
        )
        self.add_item(self.msg)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = get_guild_config(self.guild_id)
        if self.tipo == "ticket_mensagem":
            cfg["ticket"]["mensagem"] = self.msg.value
        else:
            cfg[self.tipo]["mensagem"] = self.msg.value
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message("✅ Mensagem salva!", ephemeral=True)

# ---------- Selects ----------
class SelectCanalView(discord.ui.View):
    def __init__(self, guild_id, destino, tipo_canal="text"):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.destino = destino
        tipos = [discord.ChannelType.text] if tipo_canal == "text" else [discord.ChannelType.category]
        sel = discord.ui.ChannelSelect(placeholder="Selecione o canal", channel_types=tipos, min_values=1, max_values=1)
        sel.callback = self.salvar_canal
        self.add_item(sel)

    async def salvar_canal(self, interaction: discord.Interaction):
        canal = interaction.data["values"][0]
        cfg = get_guild_config(self.guild_id)
        if self.destino == "logs":
            cfg["logs"]["canal"] = int(canal)
        elif self.destino == "ticket_painel":
            cfg["ticket"]["canal_painel"] = int(canal)
        elif self.destino == "ticket_categoria":
            cfg["ticket"]["categoria"] = int(canal)
        elif self.destino in ["entrada", "saida"]:
            cfg[self.destino]["canal"] = int(canal)
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message(f"✅ Canal salvo: <#{canal}>", ephemeral=True)

class SelectCargoView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        sel = discord.ui.RoleSelect(placeholder="Selecione o cargo suporte", min_values=1, max_values=1)
        sel.callback = self.salvar_cargo
        self.add_item(sel)

    async def salvar_cargo(self, interaction: discord.Interaction):
        cargo = interaction.data["values"][0]
        cfg = get_guild_config(self.guild_id)
        cfg["ticket"]["cargo_suporte"] = int(cargo)
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message(f"✅ Cargo suporte salvo: <@&{cargo}>", ephemeral=True)

# ---------- Views do Painel (botões organizados em fileiras) ----------
class LogsView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Canal de Logs", style=discord.ButtonStyle.secondary, emoji="📋", row=0)
    async def canal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecione o canal de logs:", view=SelectCanalView(self.guild_id, "logs"), ephemeral=True)

    @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.secondary, emoji="🔄", row=0)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_guild_config(self.guild_id)
        cfg["logs"]["ativo"] = not cfg["logs"]["ativo"]
        update_guild_config(self.guild_id, cfg)
        await interaction.response.edit_message(embed=embed_logs(self.guild_id), view=self)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=embed_painel_principal(interaction.guild, self.guild_id), view=PainelConfigView(self.guild_id))

class TicketView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Canal do Painel", style=discord.ButtonStyle.secondary, emoji="📢", row=0)
    async def canal_painel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecione o canal onde vai o painel:", view=SelectCanalView(self.guild_id, "ticket_painel"), ephemeral=True)

    @discord.ui.button(label="Mensagem do Painel", style=discord.ButtonStyle.secondary, emoji="💬", row=0)
    async def msg_painel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalMensagem(self.guild_id, "ticket_mensagem", "Mensagem do Painel"))

    @discord.ui.button(label="Cargo Suporte", style=discord.ButtonStyle.secondary, emoji="🛡️", row=0)
    async def cargo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecione o cargo que vai ser marcado nos tickets:", view=SelectCargoView(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Categoria", style=discord.ButtonStyle.secondary, emoji="📁", row=1)
    async def categoria(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecione a categoria onde os tickets vão ser criados:", view=SelectCanalView(self.guild_id, "ticket_categoria", "category"), ephemeral=True)

    @discord.ui.button(label="Enviar Painel", style=discord.ButtonStyle.secondary, emoji="📤", row=1)
    async def enviar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_guild_config(self.guild_id)
        if not cfg["ticket"]["canal_painel"]:
            await interaction.response.send_message("❌ Defina o canal do painel primeiro!", ephemeral=True)
            return
        canal = interaction.guild.get_channel(cfg["ticket"]["canal_painel"])
        if not canal:
            await interaction.response.send_message("❌ Canal não encontrado!", ephemeral=True)
            return
        embed = discord.Embed(title="🎫  Central de Atendimento", description=cfg["ticket"]["mensagem"], color=COR_PRINCIPAL)
        embed.set_footer(text="Clique no botão abaixo para abrir um ticket")
        await canal.send(embed=embed, view=TicketAbrirView())
        await interaction.response.send_message(f"✅ Painel enviado em {canal.mention}!", ephemeral=True)

    @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_guild_config(self.guild_id)
        cfg["ticket"]["ativo"] = not cfg["ticket"]["ativo"]
        update_guild_config(self.guild_id, cfg)
        await interaction.response.edit_message(embed=embed_ticket(self.guild_id), view=self)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=2)
    async def voltar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=embed_painel_principal(interaction.guild, self.guild_id), view=PainelConfigView(self.guild_id))

class EntradaSaidaView(discord.ui.View):
    def __init__(self, guild_id, tipo):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.tipo = tipo

    @discord.ui.button(label="Canal", style=discord.ButtonStyle.secondary, emoji="📢", row=0)
    async def canal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecione o canal
