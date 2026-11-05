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
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get("PORT", 8080))
    )

def keep_alive():
    t = Thread(
        target=run,
        daemon=True
    )
    t.start()

# ============================================================
#  2. CONFIGS GERAIS + BANCO
# ============================================================
ARQUIVO = "volts.json"
ARQUIVO_CONFIG = "config.json"

COR_PRINCIPAL = 0xF1C40F
COR_SUCESSO = 0x2ECC71
COR_ERRO = 0xE74C3C
COR_INFO = 0x3498DB

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
            headers={
                "Authorization": f"Bearer {UPSTASH_TOKEN}"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            if data.get("result"):
                return json.loads(data["result"])
            return {}
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
            headers={
                "Authorization": f"Bearer {UPSTASH_TOKEN}"
            },
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
            headers={
                "Authorization": f"Bearer {UPSTASH_TOKEN}"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            if data.get("result"):
                return json.loads(data["result"])
            return {}
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
            headers={
                "Authorization": f"Bearer {UPSTASH_TOKEN}"
            },
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
            "logs": {
                "ativo": False,
                "canal": None
            },
            "ticket": {
                "ativo": False,
                "canal_painel": None,
                "mensagem": (
                    "Clique no botão abaixo "
                    "para abrir um ticket!\n"
                    "Nossa equipe vai te atender "
                    "o mais rápido possível."
                ),
                "cargo_suporte": None,
                "categoria": None
            },
            "entrada": {
                "ativo": False,
                "canal": None,
                "mensagem": (
                    "👋 {user} entrou em "
                    "**{server}**!\n"
                    "Seja bem-vindo(a)!"
                )
            },
            "saida": {
                "ativo": False,
                "canal": None,
                "mensagem": (
                    "🚪 {user} saiu de "
                    "**{server}**.\n"
                    "Sentiremos sua falta!"
                )
            },
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

def parse_cor(cor_str):
    if not cor_str:
        return COR_PRINCIPAL
    cor_str = cor_str.strip().lower()
    nomes = {
        "amarelo": 0xF1C40F,
        "vermelho": 0xE74C3C,
        "verde": 0x2ECC71,
        "azul": 0x3498DB,
        "roxo": 0x9B59B6,
        "rosa": 0xFF6B9D,
        "laranja": 0xE67E22,
        "preto": 0x2C3E50,
        "branco": 0xECF0F1,
        "cinza": 0x95A5A6,
        "ciano": 0x1ABC9C,
    }
    if cor_str in nomes:
        return nomes[cor_str]
    cor_str = cor_str.replace("#", "")
    cor_str = cor_str.replace("0x", "")
    try:
        return int(cor_str, 16)
    except:
        return COR_PRINCIPAL

def formatar_mensagem(texto, membro, guild):
    texto = texto.replace("{user}", membro.mention)
    texto = texto.replace("{usuario}", membro.mention)
    texto = texto.replace("{nome}", membro.display_name)
    texto = texto.replace("{server}", guild.name)
    texto = texto.replace("{servidor}", guild.name)
    texto = texto.replace("{membros}", str(guild.member_count))
    return texto

def status_txt(ativo: bool):
    if ativo:
        return "🟢 Ativo"
    return "🔴 Desativado"

def canal_txt(canal_id):
    if canal_id:
        return "<#" + str(canal_id) + ">"
    return "`Não definido`"

def cargo_txt(cargo_id):
    if cargo_id:
        return "<@&" + str(cargo_id) + ">"
    return "`Não definido`"

def linha():
    return "────────────────────"

def fmt_volts(valor):
    txt = f"{valor:,}"
    txt = txt.replace(",", ".")
    return "**" + txt + "** volts"

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

    @discord.ui.button(
        label="Aceitar",
        style=discord.ButtonStyle.green,
        emoji="✅"
    )
    async def aceitar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.recebedor.id:
            await interaction.response.send_message(
                "Apenas o destinatário pode aceitar "
                "esta transferência.",
                ephemeral=True
            )
            return
        self.resultado = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(
        label="Recusar",
        style=discord.ButtonStyle.red,
        emoji="❌"
    )
    async def recusar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.recebedor.id:
            await interaction.response.send_message(
                "Apenas o destinatário pode recusar "
                "esta transferência.",
                ephemeral=True
            )
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
bot = commands.Bot(
    command_prefix="v",
    intents=intents
)

# ============================================================
#  EMBEDS DO PAINEL CONFIGURAR - ORGANIZADOS
# ============================================================
def embed_painel_principal(guild, guild_id):
    cfg = get_guild_config(guild_id)
    e = discord.Embed(
        title="⚙️  Painel de Configuração",
        description=(
            "Configure as funções do Ratinho "
            "neste servidor.\n"
            "Escolha uma opção abaixo:"
        ),
        color=COR_PRINCIPAL
    )
    if guild.icon:
        e.set_thumbnail(url=guild.icon.url)
    v_logs = status_txt(cfg["logs"]["ativo"])
    v_logs += "\n**Canal:** "
    v_logs += canal_txt(cfg["logs"]["canal"])
    v_logs += "\nRegistra mensagens, entradas, "
    v_logs += "saídas, bans e mais."
    e.add_field(
        name="📋  Events Logs",
        value=v_logs,
        inline=True
    )
    v_ticket = status_txt(cfg["ticket"]["ativo"])
    v_ticket += "\n**Painel:** "
    v_ticket += canal_txt(cfg["ticket"]["canal_painel"])
    v_ticket += "\nSistema de atendimento por tickets."
    e.add_field(
        name="🎫  Ticket",
        value=v_ticket,
        inline=True
    )
    v_ent = status_txt(cfg["entrada"]["ativo"])
    v_ent += "\n**Canal:** "
    v_ent += canal_txt(cfg["entrada"]["canal"])
    v_ent += "\nBoas-vindas quando alguém entra."
    e.add_field(
        name="👋  Mensagem de Entradas",
        value=v_ent,
        inline=True
    )
    v_sai = status_txt(cfg["saida"]["ativo"])
    v_sai += "\n**Canal:** "
    v_sai += canal_txt(cfg["saida"]["canal"])
    v_sai += "\nDespedida quando alguém sai."
    e.add_field(
        name="🚪  Mensagem de Saídas",
        value=v_sai,
        inline=True
    )
    e.set_footer(
        text=f"{guild.name}  •  Painel de Configuração"
    )
    return e

def embed_logs(guild_id):
    cfg = get_guild_config(guild_id)["logs"]
    e = discord.Embed(
        title="📋  Events Logs",
        description=(
            "Configure onde os logs do servidor "
            "vão aparecer."
        ),
        color=COR_PRINCIPAL
    )
    e.add_field(
        name="Status",
        value=status_txt(cfg["ativo"]),
        inline=True
    )
    e.add_field(
        name="Canal",
        value=canal_txt(cfg["canal"]),
        inline=True
    )
    e.add_field(
        name="📌  O que é registrado",
        value=(
            "• Mensagem apagada / editada\n"
            "• Membro entrou / saiu\n"
            "• Membro banido / desbanido"
        ),
        inline=False
    )
    e.set_footer(text="Events Logs  •  Ratinho")
    return e

def embed_ticket(guild_id):
    cfg = get_guild_config(guild_id)["ticket"]
    e = discord.Embed(
        title="🎫  Ticket",
        description=(
            "Configure o sistema de tickets "
            "do servidor."
        ),
        color=COR_PRINCIPAL
    )
    e.add_field(
        name="Status",
        value=status_txt(cfg["ativo"]),
        inline=True
    )
    e.add_field(
        name="Canal do Painel",
        value=canal_txt(cfg["canal_painel"]),
        inline=True
    )
    e.add_field(
        name="Cargo Suporte",
        value=cargo_txt(cfg["cargo_suporte"]),
        inline=True
    )
    e.add_field(
        name="Categoria",
        value=canal_txt(cfg["categoria"]),
        inline=True
    )
    e.add_field(
        name="💬  Mensagem do Painel",
        value=cfg["mensagem"][:1000],
        inline=False
    )
    e.set_footer(text="Ticket  •  Ratinho")
    return e

def embed_entrada_saida(guild_id, tipo):
    cfg = get_guild_config(guild_id)[tipo]
    is_entrada = tipo == "entrada"
    if is_entrada:
        titulo = "👋  Mensagem de Entradas"
        desc = "Configure a mensagem de boas-vindas."
    else:
        titulo = "🚪  Mensagem de Saídas"
        desc = "Configure a mensagem de despedida."
    e = discord.Embed(
        title=titulo,
        description=desc,
        color=COR_PRINCIPAL
    )
    e.add_field(
        name="Status",
        value=status_txt(cfg["ativo"]),
        inline=True
    )
    e.add_field(
        name="Canal",
        value=canal_txt(cfg["canal"]),
        inline=True
    )
    e.add_field(
        name="💬  Mensagem atual",
        value=cfg["mensagem"][:1000],
        inline=False
    )
    e.add_field(
        name="🔧  Variáveis disponíveis",
        value=(
            "`{user}`  •  menciona o membro\n"
            "`{nome}`  •  nome do membro\n"
            "`{server}`  •  nome do servidor\n"
            "`{membros}`  •  total de membros"
        ),
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
        if tipo == "ticket_mensagem":
            atual = cfg["ticket"]["mensagem"]
        else:
            atual = cfg[tipo]["mensagem"]
        self.msg = discord.ui.TextInput(
            label="Mensagem",
            style=discord.TextStyle.paragraph,
            placeholder="Digite a mensagem...",
            default=atual,
            max_length=1500,
            required=True
        )
        self.add_item(self.msg)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = get_guild_config(self.guild_id)
        if self.tipo == "ticket_mensagem":
            cfg["ticket"]["mensagem"] = self.msg.value
        else:
            cfg[self.tipo]["mensagem"] = self.msg.value
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message(
            "✅ Mensagem salva!",
            ephemeral=True
        )

# ---------- Selects ----------
class SelectCanalView(discord.ui.View):
    def __init__(self, guild_id, destino, tipo_canal="text"):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.destino = destino
        if tipo_canal == "text":
            tipos = [discord.ChannelType.text]
        else:
            tipos = [discord.ChannelType.category]
        sel = discord.ui.ChannelSelect(
            placeholder="Selecione o canal",
            channel_types=tipos,
            min_values=1,
            max_values=1
        )
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
        await interaction.response.send_message(
            f"✅ Canal salvo: <#{canal}>",
            ephemeral=True
        )

class SelectCargoView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        sel = discord.ui.RoleSelect(
            placeholder="Selecione o cargo suporte",
            min_values=1,
            max_values=1
        )
        sel.callback = self.salvar_cargo
        self.add_item(sel)

    async def salvar_cargo(self, interaction: discord.Interaction):
        cargo = interaction.data["values"][0]
        cfg = get_guild_config(self.guild_id)
        cfg["ticket"]["cargo_suporte"] = int(cargo)
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message(
            f"✅ Cargo suporte salvo: <@&{cargo}>",
            ephemeral=True
        )

# ---------- Views do Painel ----------
class LogsView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(
        label="Canal de Logs",
        style=discord.ButtonStyle.secondary,
        emoji="📋",
        row=0
    )
    async def canal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Selecione o canal de logs:",
            view=SelectCanalView(self.guild_id, "logs"),
            ephemeral=True
        )

    @discord.ui.button(
        label="Ativar / Desativar",
        style=discord.ButtonStyle.secondary,
        emoji="🔄",
        row=0
    )
    async def toggle(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        cfg = get_guild_config(self.guild_id)
        cfg["logs"]["ativo"] = not cfg["logs"]["ativo"]
        update_guild_config(self.guild_id, cfg)
        await interaction.response.edit_message(
            embed=embed_logs(self.guild_id),
            view=self
        )

    @discord.ui.button(
        label="Voltar",
        style=discord.ButtonStyle.secondary,
        emoji="⬅️",
        row=1
    )
    async def voltar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=embed_painel_principal(
                interaction.guild,
                self.guild_id
            ),
            view=PainelConfigView(self.guild_id)
        )

class TicketView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(
        label="Canal do Painel",
        style=discord.ButtonStyle.secondary,
        emoji="📢",
        row=0
    )
    async def canal_painel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Selecione o canal onde vai o painel:",
            view=SelectCanalView(
                self.guild_id,
                "ticket_painel"
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Mensagem do Painel",
        style=discord.ButtonStyle.secondary,
        emoji="💬",
        row=0
    )
    async def msg_painel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            ModalMensagem(
                self.guild_id,
                "ticket_mensagem",
    @discord.ui.button(
        label="Categoria",
        style=discord.ButtonStyle.secondary,
        emoji="📁",
        row=1
    )
    async def categoria(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Selecione a categoria onde os tickets "
            "vão ser criados:",
            view=SelectCanalView(
                self.guild_id,
                "ticket_categoria",
                "category"
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Enviar Painel",
        style=discord.ButtonStyle.secondary,
        emoji="📤",
        row=1
    )
    async def enviar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        cfg = get_guild_config(self.guild_id)
        if not cfg["ticket"]["canal_painel"]:
            await interaction.response.send_message(
                "❌ Defina o canal do painel primeiro!",
                ephemeral=True
            )
            return
        canal = interaction.guild.get_channel(
            cfg["ticket"]["canal_painel"]
        )
        if not canal:
            await interaction.response.send_message(
                "❌ Canal não encontrado!",
                ephemeral=True
            )
            return
        embed = discord.Embed(
            title="🎫  Central de Atendimento",
            description=cfg["ticket"]["mensagem"],
            color=COR_PRINCIPAL
        )
        embed.set_footer(
            text="Clique no botão abaixo para abrir um ticket"
        )
        await canal.send(
            embed=embed,
            view=TicketAbrirView()
        )
        await interaction.response.send_message(
            f"✅ Painel enviado em {canal.mention}!",
            ephemeral=True
        )

    @discord.ui.button(
        label="Ativar / Desativar",
        style=discord.ButtonStyle.secondary,
        emoji="🔄",
        row=1
    )
    async def toggle(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        cfg = get_guild_config(self.guild_id)
        cfg["ticket"]["ativo"] = not cfg["ticket"]["ativo"]
        update_guild_config(self.guild_id, cfg)
        await interaction.response.edit_message(
            embed=embed_ticket(self.guild_id),
            view=self
        )

    @discord.ui.button(
        label="Voltar",
        style=discord.ButtonStyle.secondary,
        emoji="⬅️",
        row=2
    )
    async def voltar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=embed_painel_principal(
                interaction.guild,
                self.guild_id
            ),
            view=PainelConfigView(self.guild_id)
        )

class EntradaSaidaView(discord.ui.View):
    def __init__(self, guild_id, tipo):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.tipo = tipo

    @discord.ui.button(
        label="Canal",
        style=discord.ButtonStyle.secondary,
        emoji="📢",
        row=0
    )
    async def canal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Selecione o canal:",
            view=SelectCanalView(self.guild_id, self.tipo),
            ephemeral=True
        )

    @discord.ui.button(
        label="Mensagem",
        style=discord.ButtonStyle.secondary,
        emoji="💬",
        row=0
    )
    async def msg(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.tipo == "entrada":
            titulo = "Mensagem de Entrada"
        else:
            titulo = "Mensagem de Saída"
        await interaction.response.send_modal(
            ModalMensagem(self.guild_id, self.tipo, titulo)
        )

    @discord.ui.button(
        label="Ativar / Desativar",
        style=discord.ButtonStyle.secondary,
        emoji="🔄",
        row=0
    )
    async def toggle(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        cfg = get_guild_config(self.guild_id)
        cfg[self.tipo]["ativo"] = not cfg[self.tipo]["ativo"]
        update_guild_config(self.guild_id, cfg)
        await interaction.response.edit_message(
            embed=embed_entrada_saida(
                self.guild_id,
                self.tipo
            ),
            view=self
        )

    @discord.ui.button(
        label="Testar",
        style=discord.ButtonStyle.secondary,
        emoji="🧪",
        row=1
    )
    async def testar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        cfg = get_guild_config(self.guild_id)[self.tipo]
        if not cfg["canal"]:
            await interaction.response.send_message(
                "❌ Defina o canal primeiro!",
                ephemeral=True
            )
            return
        canal = interaction.guild.get_channel(cfg["canal"])
        texto = formatar_mensagem(
            cfg["mensagem"],
            interaction.user,
            interaction.guild
        )
        await canal.send(
            embed=discord.Embed(
                description=texto,
                color=COR_PRINCIPAL
            )
        )
        await interaction.response.send_message(
            "✅ Teste enviado!",
            ephemeral=True
        )

    @discord.ui.button(
        label="Voltar",
        style=discord.ButtonStyle.secondary,
        emoji="⬅️",
        row=1
    )
    async def voltar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=embed_painel_principal(
                interaction.guild,
                self.guild_id
            ),
            view=PainelConfigView(self.guild_id)
        )

class PainelConfigView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(
        label="Events Logs",
        style=discord.ButtonStyle.secondary,
        emoji="📋",
        row=0
    )
    async def logs(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=embed_logs(self.guild_id),
            view=LogsView(self.guild_id)
        )

    @discord.ui.button(
        label="Ticket",
        style=discord.ButtonStyle.secondary,
        emoji="🎫",
        row=0
    )
    async def ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=embed_ticket(self.guild_id),
            view=TicketView(self.guild_id)
        )

    @discord.ui.button(
        label="Mensagem de Entradas",
        style=discord.ButtonStyle.secondary,
        emoji="👋",
        row=1
    )
    async def entrada(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=embed_entrada_saida(
                self.guild_id,
                "entrada"
            ),
            view=EntradaSaidaView(self.guild_id, "entrada")
        )

    @discord.ui.button(
        label="Mensagem de Saídas",
        style=discord.ButtonStyle.secondary,
        emoji="🚪",
        row=1
    )
    async def saida(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=embed_entrada_saida(
                self.guild_id,
                "saida"
            ),
            view=EntradaSaidaView(self.guild_id, "saida")
        )

class TicketAbrirView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Abrir Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="abrir_ticket"
    )
    async def abrir(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        cfg = get_guild_config(interaction.guild_id)
        if not cfg["ticket"]["ativo"]:
            await interaction.response.send_message(
                "❌ Sistema de ticket desativado no momento.",
                ephemeral=True
            )
            return
        for ch in interaction.guild.text_channels:
            nome = "ticket-" + interaction.user.name.lower()
            if ch.name.startswith(nome):
                await interaction.response.send_message(
                    f"❌ Você já tem um ticket aberto: {ch.mention}",
                    ephemeral=True
                )
                return
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True
            )
        }
        if cfg["ticket"]["cargo_suporte"]:
            cargo = interaction.guild.get_role(
                cfg["ticket"]["cargo_suporte"]
            )
            if cargo:
                overwrites[cargo] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
        if cfg["ticket"]["categoria"]:
            categoria = interaction.guild.get_channel(
                cfg["ticket"]["categoria"]
            )
        else:
            categoria = None
        canal = await interaction.guild.create_text_channel(
            "ticket-" + interaction.user.name,
            overwrites=overwrites,
            category=categoria
        )
        embed = discord.Embed(
            title="🎫  Ticket Aberto",
            description=(
                f"Olá {interaction.user.mention}! "
                "Descreva seu problema que a equipe "
                "vai te atender."
            ),
            color=COR_PRINCIPAL
        )
        ping = ""
        if cfg["ticket"]["cargo_suporte"]:
            ping = "<@&" + str(cfg["ticket"]["cargo_suporte"]) + ">"
        await canal.send(
            content=ping,
            embed=embed,
            view=TicketFecharView()
        )
        await interaction.response.send_message(
            f"✅ Ticket criado: {canal.mention}",
            ephemeral=True
        )

class TicketFecharView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="fechar_ticket"
    )
    async def fechar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "🔒 Fechando ticket em 5 segundos..."
        )
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(
                reason="Ticket fechado"
            )
        except:
            pass

# ============================================================
#  5. EVENTOS - LOGS / ENTRADA / SAÍDA
# ============================================================
async def enviar_log(guild, titulo, desc, cor=COR_INFO):
    cfg = get_guild_config(guild.id)
    if not cfg["logs"]["ativo"]:
        return
    if not cfg["logs"]["canal"]:
        return
    canal = guild.get_channel(cfg["logs"]["canal"])
    if not canal:
        return
    embed = discord.Embed(
        title=titulo,
        description=desc,
        color=cor,
        timestamp=discord.utils.utcnow()
    )
    try:
        await canal.send(embed=embed)
    except:
        pass

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    bot.add_view(TicketAbrirView())
    bot.add_view(TicketFecharView())
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos slash!")
    except Exception as e:
        print(f"Erro ao sincronizar slash: {e}")
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

@bot.event
async def on_member_join(member):
    cfg = get_guild_config(member.guild.id)
    if cfg["entrada"]["ativo"] and cfg["entrada"]["canal"]:
        canal = member.guild.get_channel(cfg["entrada"]["canal"])
        if canal:
            texto = formatar_mensagem(
                cfg["entrada"]["mensagem"],
                member,
                member.guild
            )
            e = discord.Embed(
                description=texto,
                color=COR_SUCESSO
            )
            e.set_thumbnail(url=member.display_avatar.url)
            await canal.send(embed=e)
    await enviar_log(
        member.guild,
        "👋  Membro Entrou",
        (
            f"{member.mention} (`{member.id}`) "
            "entrou no servidor.\n"
            f"Conta criada em: "
            f"<t:{int(member.created_at.timestamp())}:R>"
        ),
        COR_SUCESSO
    )

@bot.event
async def on_member_remove(member):
    cfg = get_guild_config(member.guild.id)
    if cfg["saida"]["ativo"] and cfg["saida"]["canal"]:
        canal = member.guild.get_channel(cfg["saida"]["canal"])
        if canal:
            texto = formatar_mensagem(
                cfg["saida"]["mensagem"],
                member,
                member.guild
            )
            await canal.send(
                embed=discord.Embed(
                    description=texto,
                    color=COR_ERRO
                )
            )
    await enviar_log(
        member.guild,
        "🚪  Membro Saiu",
        f"**{member}** (`{member.id}`) saiu do servidor.",
        COR_ERRO
    )

@bot.event
async def on_message_delete(message):
    if not message.guild:
        return
    if message.author.bot:
        return
    txt = f"**Autor:** {message.author.mention}\n"
    txt += f"**Canal:** {message.channel.mention}\n"
    txt += "**Conteúdo:**\n"
    if message.content:
        txt += message.content[:1000]
    else:
        txt += "*sem texto*"
    await enviar_log(
        message.guild,
        "🗑️  Mensagem Apagada",
        txt,
        COR_ERRO
    )

@bot.event
async def on_message_edit(before, after):
    if not before.guild:
        return
    if before.author.bot:
        return
    if before.content == after.content:
        return
    txt = f"**Autor:** {before.author.mention}\n"
    txt += f"**Canal:** {before.channel.mention}\n"
    txt += "**Antes:**\n"
    txt += before.content[:500]
    txt += "\n**Depois:**\n"
    txt += after.content[:500]
    await enviar_log(
        before.guild,
        "✏️  Mensagem Editada",
        txt,
        COR_INFO
    )

@bot.event
async def on_member_ban(guild, user):
    await enviar_log(
        guild,
        "🔨  Membro Banido",
        f"**{user}** (`{user.id}`) foi banido.",
        COR_ERRO
    )

@bot.event
async def on_member_unban(guild, user):
    await enviar_log(
        guild,
        "✅  Membro Desbanido",
        f"**{user}** (`{user.id}`) foi desbanido.",
        COR_SUCESSO
    )

# ============================================================
#  6. COMANDOS
# ============================================================
@bot.hybrid_command(
    name="atm",
    description="Consulta o saldo de volts"
)
async def atm(ctx, membro: discord.Member = None):
    if membro is None:
        membro = ctx.author
    saldo = get_volts(membro.id)
    embed = discord.Embed(
        title="🏦  Banco Volts",
        description=f"Saldo atual de **{membro.display_name}**",
        color=COR_PRINCIPAL,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(
        name="⚡ Volts",
        value=fmt_volts(saldo),
        inline=False
    )
    embed.set_footer(
        text=f"Solicitado por {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.send(embed=embed)

@bot.hybrid_group(
    name="volts",
    description="Sistema Volts",
    invoke_without_command=True
)
async def volts_group(ctx):
    embed = discord.Embed(
        title="⚡  Sistema Volts",
        description="Comandos disponíveis:",
        color=COR_INFO
    )
    embed.add_field(
        name="v volts pagar",
        value=(
            "`v volts pagar @usuário <valor>`\n"
            "Realiza uma transferência com confirmação."
        ),
        inline=False
    )
    embed.add_field(
        name="v atm",
        value=(
            "`v atm` ou `v atm @usuário`\n"
            "Consulta o saldo de volts."
        ),
        inline=False
    )
    embed.add_field(
        name="v daily",
        value=(
            "`v daily`\n"
            "Resgata sua recompensa diária."
        ),
        inline=False
    )
    embed.set_footer(
        text=f"Solicitado por {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.send(embed=embed)

@volts_group.command(
    name="pagar",
    description="Realiza uma transferência com confirmação"
)
async def volts_pagar(
    ctx,
    membro: discord.Member = None,
    valor: int = None
):
    if membro is None or valor is None:
        embed = discord.Embed(
            title="⚠️  Uso incorreto",
            description="Utilize o comando da seguinte forma:",
            color=COR_ERRO
        )
        embed.add_field(
            name="Formato",
            value="`v volts pagar @usuário <valor>`",
            inline=False
        )
        embed.add_field(
            name="Exemplo",
            value="`v volts pagar @Shy 500`",
            inline=False
        )
        await ctx.send(embed=embed)
        return
    if membro.id == ctx.author.id:
        await ctx.send(
            embed=discord.Embed(
                title="⚠️  Transferência inválida",
                description=(
                    "Você não pode realizar uma transferência "
                    "para si mesmo."
                ),
                color=COR_ERRO
            )
        )
        return
    if valor <= 0:
        await ctx.send(
            embed=discord.Embed(
                title="⚠️  Valor inválido",
                description=(
                    "O valor da transferência deve ser "
                    "maior que zero."
                ),
                color=COR_ERRO
            )
        )
        return
    saldo = get_volts(ctx.author.id)
    if saldo < valor:
        embed = discord.Embed(
            title="❌  Saldo insuficiente",
            description=(
                "Você não possui volts suficientes "
                "para concluir esta transferência."
            ),
            color=COR_ERRO
        )
        embed.add_field(
            name="Seu saldo",
            value="⚡ " + fmt_volts(saldo),
               inline=True
        )
        embed.add_field(
            name="Valor solicitado",
            value="⚡ " + fmt_volts(valor),
            inline=True
        )
        await ctx.send(embed=embed)
        return
    view = ConfirmarPagamento(ctx.author, membro, valor)
    embed = discord.Embed(
        title="💸  Solicitação de Transferência",
        description=(
            f"{membro.mention}, você recebeu uma "
            "solicitação de transferência."
        ),
        color=COR_INFO
    )
    embed.add_field(
        name="Remetente",
        value=ctx.author.mention,
        inline=True
    )
    embed.add_field(
        name="Destinatário",
        value=membro.mention,
        inline=True
    )
    embed.add_field(
        name="Valor",
        value="⚡ " + fmt_volts(valor),
        inline=False
    )
    embed.set_footer(
        text="Você possui 60 segundos para responder."
    )
    msg = await ctx.send(embed=embed, view=view)
    await view.wait()
    if view.resultado is None:
        await msg.edit(
            embed=discord.Embed(
                title="⏰  Tempo esgotado",
                description=(
                    "A solicitação de transferência expirou "
                    "e foi cancelada automaticamente."
                ),
                color=COR_ERRO
            ),
            view=None
        )
        return
    if view.resultado is False:
        e = discord.Embed(
            title="❌  Transferência recusada",
            description=(
                f"{membro.mention} recusou a transferência."
            ),
            color=COR_ERRO
        )
        e.add_field(
            name="Valor",
            value="⚡ " + fmt_volts(valor),
            inline=False
        )
        await msg.edit(embed=e, view=None)
        return
    add_volts(ctx.author.id, -valor)
    add_volts(membro.id, valor)
    novo_pagador = get_volts(ctx.author.id)
    novo_recebedor = get_volts(membro.id)
    e = discord.Embed(
        title="✅  Transferência concluída",
        description=(
            "A transferência foi confirmada com sucesso."
        ),
        color=COR_SUCESSO
    )
    e.add_field(
        name="Remetente",
        value=(
            f"{ctx.author.mention}\n"
            "Saldo atual: ⚡ " + fmt_volts(novo_pagador)
        ),
        inline=True
    )
    e.add_field(
        name="Destinatário",
        value=(
            f"{membro.mention}\n"
            "Saldo atual: ⚡ " + fmt_volts(novo_recebedor)
        ),
        inline=True
    )
    e.add_field(
        name="Valor transferido",
        value="⚡ " + fmt_volts(valor),
        inline=False
    )
    await msg.edit(embed=e, view=None)

@bot.hybrid_command(
    name="daily",
    description="Resgata sua recompensa diária"
)
async def daily(ctx):
    dados = carregar()
    uid = str(ctx.author.id)
    agora = time.time()
    if uid not in dados:
        dados[uid] = {"volts": 0, "last_daily": 0}
    falta = 86400 - (agora - dados[uid].get("last_daily", 0))
    if falta > 0:
        horas = int(falta // 3600)
        minutos = int((falta % 3600) // 60)
        embed = discord.Embed(
            title="⏰  Recompensa diária indisponível",
            description=(
                "Você já resgatou sua recompensa diária."
            ),
            color=COR_ERRO
        )
        embed.add_field(
            name="Próximo resgate em",
            value=f"**{horas}h {minutos}min**",
            inline=False
        )
        embed.set_footer(
            text=f"Solicitado por {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)
        return
    ganho = random.randint(2000, 5000)
    dados[uid]["volts"] += ganho
    dados[uid]["last_daily"] = agora
    salvar(dados)
    embed = discord.Embed(
        title="🎉  Recompensa Diária Resgatada",
        description=f"Parabéns, {ctx.author.mention}!",
        color=COR_SUCESSO
    )
    embed.add_field(
        name="Valor recebido",
        value="⚡ " + fmt_volts(ganho),
        inline=True
    )
    embed.add_field(
        name="Saldo atual",
        value="⚡ " + fmt_volts(dados[uid]["volts"]),
        inline=True
    )
    embed.add_field(
        name="Próximo resgate",
        value="Disponível em 24 horas.",
        inline=False
    )
    embed.set_footer(
        text=f"Solicitado por {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(
    name="configurar",
    description="Painel de configuração do servidor (só ADM)"
)
@app_commands.default_permissions(administrator=True)
@commands.has_permissions(administrator=True)
async def configurar(ctx):
    if ctx.guild is None:
        await ctx.send(
            "❌ Use esse comando em um servidor!",
            ephemeral=True
        )
        return
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(
            "❌ Você precisa ser administrador!",
            ephemeral=True
        )
        return
    await ctx.send(
        embed=embed_painel_principal(
            ctx.guild,
            ctx.guild.id
        ),
        view=PainelConfigView(ctx.guild.id)
    )

@configurar.error
async def configurar_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Você precisa ser administrador!",
            ephemeral=True
        )

@bot.tree.command(
    name="embed",
    description="Cria um embed personalizado (só ADM)"
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    mensagem="Mensagem do embed (obrigatório)",
    cor="Cor: nome ou #hex. Se vazio, fica amarelo",
    midia="Link de imagem (opcional)"
)
async def criar_embed(
    interaction: discord.Interaction,
    mensagem: str,
    cor: str = None,
    midia: str = None
):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        description=mensagem,
        color=parse_cor(cor)
    )
    if midia and midia.strip().startswith("http"):
        embed.set_image(url=midia.strip())
    await interaction.channel.send(embed=embed)
    await interaction.followup.send(
        "✅ Embed enviado!",
        ephemeral=True
    )

@criar_embed.error
async def criar_embed_error(
    interaction: discord.Interaction,
    error
):
    if isinstance(error, app_commands.errors.MissingPermissions):
        msg = (
            "❌ Você precisa ser administrador "
            "para usar esse comando."
        )
    else:
        msg = f"❌ Erro: {error}"
    if not interaction.response.is_done():
        await interaction.response.send_message(
            msg,
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            msg,
            ephemeral=True
        )

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    conteudo_sem_mencao = re.sub(
        r"<@!?\d+>",
        "",
        message.content
    ).strip()
    if bot.user in message.mentions and conteudo_sem_mencao == "":
        embed = discord.Embed(
            title="👋  Olá!",
            description=(
                f"{message.author.mention}, "
                "eu sou o **Ratinho**."
            ),
            color=COR_PRINCIPAL
        )
        embed.add_field(
            name="Prefixo",
            value="`v`",
            inline=False
        )
        embed.add_field(
            name="Exemplo",
            value=(
                "`v atm` • `v daily` • "
                "`v volts pagar @usuário 100` • "
                "`v configurar`"
            ),
            inline=False
        )
        await message.channel.send(embed=embed)
    await bot.process_commands(message)

keep_alive()
bot.run(os.getenv("TOKEN"))    
