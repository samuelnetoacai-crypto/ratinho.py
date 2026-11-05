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
import uuid
from datetime import timedelta

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
                "canal_painel": None,
                "mensagem": (
                    "Clique no botão abaixo "
                    "para abrir um ticket!\n"
                    "Nossa equipe vai te atender "
                    "o mais rápido possível."
                ),
                "cargo_suporte": None,
                "categoria": None,
                "botoes": [{"id": "suporte", "nome": "Suporte", "cor": "azul", "cargo_suporte": None}]
            },
            "entrada": {
                "ativo": False,
                "canal": None,
                "mensagem": (
                    "👋 {user} entrou em "
                    "**{server}**!\n"
                    "Seja bem-vindo(a)!"
                ),
                "cor": "verde",
                "imagem": None
            },
            "saida": {
                "ativo": False,
                "canal": None,
                "mensagem": (
                    "🚪 {user} saiu de "
                    "**{server}**.\n"
                    "Sentiremos sua falta!"
                ),
                "cor": "vermelho",
                "imagem": None
            },
        }
        salvar_config(dados)

    dados[gid].setdefault("entrada", {}).setdefault("cor", "verde")
    dados[gid]["entrada"].setdefault("imagem", None)
    dados[gid].setdefault("saida", {}).setdefault("cor", "vermelho")
    dados[gid]["saida"].setdefault("imagem", None)
    dados[gid].setdefault("ticket", {}).setdefault("cor", "amarelo")
    dados[gid]["ticket"].setdefault("imagem", None)
    ticket_cfg = dados[gid].setdefault("ticket", {})
    ticket_cfg.setdefault("botoes", [{
        "id": "suporte", "nome": "Suporte", "cor": "azul",
        "cargo_suporte": ticket_cfg.get("cargo_suporte")
    }])
    for item in ticket_cfg["botoes"]:
        item.setdefault("id", uuid.uuid4().hex[:10])
        item.setdefault("nome", "Suporte")
        item.setdefault("cor", "azul")
        item.setdefault("cargo_suporte", ticket_cfg.get("cargo_suporte"))
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
        title="⚙️ Central de Configuração",
        description=(
            "Gerencie os recursos do Ratinho neste servidor.\n"
            "Selecione uma categoria para consultar e ajustar as configurações disponíveis."
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
        name="📋  Registro de eventos",
        value=v_logs,
        inline=True
    )
    v_ticket = "**Painel:** " + canal_txt(cfg["ticket"]["canal_painel"])
    v_ticket += f"\n**Tipos de ticket:** {len(cfg['ticket'].get('botoes', []))}"
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
    e.set_footer(text="Registro de eventos • Ratinho")
    return e

def embed_ticket(guild_id):
    cfg = get_guild_config(guild_id)["ticket"]
    botoes = cfg.get("botoes", [])
    resumo = "\\n".join(
        f"• **{b['nome']}** — {b.get('cor', 'azul')} — {cargo_txt(b.get('cargo_suporte'))}"
        for b in botoes
    ) or "`Nenhum botão criado`"
    e = discord.Embed(
        title="🎫  Configuração de Tickets",
        description="Crie vários tipos de atendimento e personalize o nome, a cor e o cargo responsável por cada botão.",
        color=parse_cor(cfg.get("cor") or "amarelo")
    )
    if cfg.get("imagem"):
        e.set_image(url=cfg["imagem"])
    e.add_field(name="Canal do Painel", value=canal_txt(cfg.get("canal_painel")), inline=True)
    e.add_field(name="Categoria", value=canal_txt(cfg.get("categoria")), inline=True)
    e.add_field(name=f"Botões configurados ({len(botoes)})", value=resumo[:1024], inline=False)
    e.add_field(name="Mensagem do Painel", value=cfg.get("mensagem", "")[:1000], inline=False)
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
        color=parse_cor(cfg.get("cor") or ("verde" if is_entrada else "vermelho"))
    )
    if cfg.get("imagem"):
        e.set_image(url=cfg["imagem"])
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

class ModalAparencia(discord.ui.Modal):
    def __init__(self, guild_id, tipo):
        super().__init__(title="Personalizar aparência")
        self.guild_id = guild_id
        self.tipo = tipo
        cfg = get_guild_config(guild_id)[tipo]
        self.cor = discord.ui.TextInput(
            label="Cor (nome ou código hexadecimal)",
            placeholder="Ex.: amarelo ou #F1C40F",
            default=str(cfg.get("cor") or "amarelo"),
            required=False,
            max_length=20
        )
        self.imagem = discord.ui.TextInput(
            label="URL da imagem (deixe vazio para remover)",
            placeholder="https://...",
            default=str(cfg.get("imagem") or ""),
            required=False,
            max_length=400
        )
        self.add_item(self.cor)
        self.add_item(self.imagem)

    async def on_submit(self, interaction: discord.Interaction):
        cor = self.cor.value.strip() or "amarelo"
        imagem = self.imagem.value.strip() or None
        if imagem and not imagem.lower().startswith(("https://", "http://")):
            await interaction.response.send_message("❌ A imagem precisa ser um link HTTP ou HTTPS válido.", ephemeral=True)
            return
        cfg = get_guild_config(self.guild_id)
        cfg[self.tipo]["cor"] = cor
        cfg[self.tipo]["imagem"] = imagem
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message("✅ Aparência salva com sucesso!", ephemeral=True)

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

class ModalBotaoTicket(discord.ui.Modal):
    def __init__(self, guild_id, botao_id=None):
        super().__init__(title="Criar botão de ticket" if botao_id is None else "Editar botão de ticket")
        self.guild_id = guild_id
        self.botao_id = botao_id
        atual = next((b for b in get_guild_config(guild_id)["ticket"].get("botoes", []) if b["id"] == botao_id), {})
        self.nome = discord.ui.TextInput(label="Nome do botão", placeholder="Ex.: Suporte, Parcerias, Dúvidas", default=atual.get("nome", ""), max_length=40)
        self.cor = discord.ui.TextInput(label="Cor do botão (azul, verde, vermelho ou cinza)", placeholder="Ex.: azul, verde, vermelho ou cinza", default=atual.get("cor", "azul"), max_length=20)
        self.add_item(self.nome)
        self.add_item(self.cor)

    async def on_submit(self, interaction):
        cor_escolhida = self.cor.value.strip().lower()
        if cor_escolhida not in ("azul", "verde", "vermelho", "cinza"):
            await interaction.response.send_message(
                "❌ Escolha uma destas cores: azul, verde, vermelho ou cinza. "
                "O Discord só permite essas quatro cores nos botões.",
                ephemeral=True
            )
            return
        cfg = get_guild_config(self.guild_id)
        botoes = cfg["ticket"].setdefault("botoes", [])
        if self.botao_id:
            botao = next((b for b in botoes if b["id"] == self.botao_id), None)
            if not botao:
                await interaction.response.send_message("❌ Botão não encontrado.", ephemeral=True)
                return
            botao["nome"], botao["cor"] = self.nome.value.strip(), cor_escolhida
        else:
            if len(botoes) >= 25:
                await interaction.response.send_message("❌ O Discord permite no máximo 25 botões por painel.", ephemeral=True)
                return
            botao = {"id": uuid.uuid4().hex[:10], "nome": self.nome.value.strip(), "cor": cor_escolhida, "cargo_suporte": None}
            botoes.append(botao)
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message(
            f"✅ Botão **{botao['nome']}** salvo! Escolha o cargo responsável:",
            view=SelectCargoBotaoView(self.guild_id, botao["id"]), ephemeral=True
        )


class SelectCargoBotaoView(discord.ui.View):
    def __init__(self, guild_id, botao_id):
        super().__init__(timeout=120)
        self.guild_id, self.botao_id = guild_id, botao_id
        sel = discord.ui.RoleSelect(placeholder="Selecione o cargo de suporte", min_values=1, max_values=1)
        sel.callback = self.salvar_cargo
        self.add_item(sel)

    async def salvar_cargo(self, interaction):
        cargo_id = int(interaction.data["values"][0])
        cfg = get_guild_config(self.guild_id)
        botao = next((b for b in cfg["ticket"].get("botoes", []) if b["id"] == self.botao_id), None)
        if not botao:
            await interaction.response.send_message("❌ Botão não encontrado.", ephemeral=True)
            return
        botao["cargo_suporte"] = cargo_id
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message(f"✅ Cargo de suporte salvo: <@&{cargo_id}>", ephemeral=True)


class GerenciarBotaoTicketView(discord.ui.View):
    def __init__(self, guild_id, botao_id):
        super().__init__(timeout=120)
        self.guild_id, self.botao_id = guild_id, botao_id

    @discord.ui.button(label="Editar nome e cor", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def editar(self, interaction, button):
        await interaction.response.send_modal(ModalBotaoTicket(self.guild_id, self.botao_id))

    @discord.ui.button(label="Alterar cargo", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def cargo(self, interaction, button):
        await interaction.response.send_message("Selecione o cargo responsável:", view=SelectCargoBotaoView(self.guild_id, self.botao_id), ephemeral=True)

    @discord.ui.button(label="Excluir botão", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def excluir(self, interaction, button):
        cfg = get_guild_config(self.guild_id)
        cfg["ticket"]["botoes"] = [b for b in cfg["ticket"].get("botoes", []) if b["id"] != self.botao_id]
        update_guild_config(self.guild_id, cfg)
        await interaction.response.edit_message(content="✅ Botão removido.", view=None)


class SelectGerenciarBotaoTicketView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        botoes = get_guild_config(guild_id)["ticket"].get("botoes", [])
        options = [discord.SelectOption(label=b["nome"][:100], value=b["id"]) for b in botoes[:25]]
        if options:
            sel = discord.ui.Select(placeholder="Escolha o botão para gerenciar", options=options)
            sel.callback = self.selecionar
            self.add_item(sel)

    async def selecionar(self, interaction):
        await interaction.response.send_message(
            "O que deseja fazer com esse botão?",
            view=GerenciarBotaoTicketView(self.guild_id, interaction.data["values"][0]),
            ephemeral=True
        )


class TicketView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Canal do Painel", style=discord.ButtonStyle.secondary, emoji="📢", row=0)
    async def canal_painel(self, interaction, button):
        await interaction.response.send_message("Selecione o canal onde vai o painel:", view=SelectCanalView(self.guild_id, "ticket_painel"), ephemeral=True)

    @discord.ui.button(label="Mensagem do Painel", style=discord.ButtonStyle.secondary, emoji="💬", row=0)
    async def msg_painel(self, interaction, button):
        await interaction.response.send_modal(ModalMensagem(self.guild_id, "ticket_mensagem", "Mensagem do Painel"))

    @discord.ui.button(label="Categoria", style=discord.ButtonStyle.secondary, emoji="📁", row=0)
    async def categoria(self, interaction, button):
        await interaction.response.send_message("Selecione a categoria onde os tickets serão criados:", view=SelectCanalView(self.guild_id, "ticket_categoria", "category"), ephemeral=True)

    @discord.ui.button(label="Personalizar aparência", style=discord.ButtonStyle.secondary, emoji="🎨", row=1)
    async def aparencia(self, interaction, button):
        await interaction.response.send_modal(ModalAparencia(self.guild_id, "ticket"))

    @discord.ui.button(label="Adicionar botão", style=discord.ButtonStyle.secondary, emoji="➕", row=1)
    async def adicionar(self, interaction, button):
        await interaction.response.send_modal(ModalBotaoTicket(self.guild_id))

    @discord.ui.button(label="Gerenciar botões", style=discord.ButtonStyle.secondary, emoji="🛠️", row=1)
    async def gerenciar(self, interaction, button):
        if not get_guild_config(self.guild_id)["ticket"].get("botoes"):
            await interaction.response.send_message("Você ainda não criou botões.", ephemeral=True)
            return
        await interaction.response.send_message("Selecione um botão para editar, trocar o cargo ou excluir:", view=SelectGerenciarBotaoTicketView(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Enviar Painel", style=discord.ButtonStyle.secondary, emoji="📤", row=2)
    async def enviar(self, interaction, button):
        cfg = get_guild_config(self.guild_id)["ticket"]
        if not cfg.get("canal_painel"):
            await interaction.response.send_message("❌ Defina o canal do painel primeiro!", ephemeral=True)
            return
        if not cfg.get("botoes"):
            await interaction.response.send_message("❌ Crie pelo menos um botão antes de enviar o painel.", ephemeral=True)
            return
        canal = interaction.guild.get_channel(cfg["canal_painel"])
        if not canal:
            await interaction.response.send_message("❌ Canal não encontrado!", ephemeral=True)
            return
        embed = discord.Embed(title="🎫  Central de Atendimento", description=cfg["mensagem"], color=parse_cor(cfg.get("cor")))
        if cfg.get("imagem"):
            embed.set_image(url=cfg["imagem"])
        embed.set_footer(text="Escolha abaixo o tipo de atendimento desejado")
        await canal.send(embed=embed, view=TicketAbrirView(self.guild_id))
        await interaction.response.send_message(f"✅ Painel enviado em {canal.mention}!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=3)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_painel_principal(interaction.guild, self.guild_id), view=PainelConfigView(self.guild_id))


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

    @discord.ui.button(label="Ativar / Desativar", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_guild_config(self.guild_id)
        cfg[self.tipo]["ativo"] = not cfg[self.tipo]["ativo"]
        update_guild_config(self.guild_id, cfg)
        await interaction.response.edit_message(embed=embed_entrada_saida(self.guild_id, self.tipo), view=self)

    @discord.ui.button(label="Personalizar aparência", style=discord.ButtonStyle.secondary, emoji="🎨", row=1)
    async def aparencia(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalAparencia(self.guild_id, self.tipo))

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

def estilo_botao_ticket(cor):
    valor = str(cor or "azul").strip().lower()
    estilos = {
        "azul": discord.ButtonStyle.primary,
        "verde": discord.ButtonStyle.success,
        "vermelho": discord.ButtonStyle.danger,
        "cinza": discord.ButtonStyle.secondary
    }
    return estilos.get(valor, discord.ButtonStyle.secondary)


class TicketTipoButton(discord.ui.Button):
    def __init__(self, guild_id, dados):
        self.guild_id = guild_id
        self.botao_id = dados["id"]
        super().__init__(
            label=dados.get("nome", "Ticket")[:80],
            style=estilo_botao_ticket(dados.get("cor")),
            custom_id=f"ratinho_ticket:{guild_id}:{self.botao_id}"
        )

    async def callback(self, interaction):
        await abrir_ticket_tipo(interaction, self.botao_id)


class TicketAbrirView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        for dados in get_guild_config(guild_id)["ticket"].get("botoes", [])[:25]:
            self.add_item(TicketTipoButton(guild_id, dados))


async def abrir_ticket_tipo(interaction, botao_id):
    cfg = get_guild_config(interaction.guild_id)["ticket"]
    dados = next((b for b in cfg.get("botoes", []) if b["id"] == botao_id), None)
    if not dados:
        await interaction.response.send_message("❌ Esse tipo de ticket não está mais disponível.", ephemeral=True)
        return

    nome_limpo = re.sub(r"[^a-z0-9-]", "-", interaction.user.name.lower())
    nome_limpo = re.sub(r"-+", "-", nome_limpo).strip("-") or str(interaction.user.id)
    prefixo = f"ticket-{nome_limpo}"
    for ch in interaction.guild.text_channels:
        if ch.topic and f"ticket_owner:{interaction.user.id}" in ch.topic:
            await interaction.response.send_message(f"❌ Você já tem um ticket aberto: {ch.mention}", ephemeral=True)
            return

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    }
    bot_member = interaction.guild.me
    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    cargo_id = dados.get("cargo_suporte")
    if cargo_id:
        cargo = interaction.guild.get_role(int(cargo_id))
        if cargo:
            overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    categoria = interaction.guild.get_channel(cfg["categoria"]) if cfg.get("categoria") else None
    canal = await interaction.guild.create_text_channel(
        name=f"{prefixo}-{dados['id'][:5]}"[:100],
        overwrites=overwrites,
        category=categoria,
        topic=f"ticket_owner:{interaction.user.id} | tipo:{dados['id']}"
    )
    embed = discord.Embed(
        title=f"🎫  {dados.get('nome', 'Ticket')} aberto",
        description=f"Olá {interaction.user.mention}! Descreva o que precisa e a equipe responsável irá atender você.",
        color=parse_cor(cfg.get("cor") or dados.get("cor"))
    )
    if cfg.get("imagem"):
        embed.set_image(url=cfg["imagem"])
    ping = f"<@&{cargo_id}>" if cargo_id else ""
    await canal.send(content=ping, embed=embed, view=TicketFecharView(), allowed_mentions=discord.AllowedMentions(roles=True))
    await interaction.response.send_message(f"✅ Ticket criado: {canal.mention}", ephemeral=True)



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
    bot.add_view(TicketFecharView())
    for guild in bot.guilds:
        try:
            bot.add_view(TicketAbrirView(guild.id))
        except Exception as e:
            print(f"Erro ao registrar painel de tickets de {guild.id}: {e}")
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
                color=parse_cor(cfg["entrada"].get("cor") or "verde")
            )
            e.set_thumbnail(url=member.display_avatar.url)
            if cfg["entrada"].get("imagem"):
                e.set_image(url=cfg["entrada"]["imagem"])
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
            embed_saida = discord.Embed(
                description=texto,
                color=parse_cor(cfg["saida"].get("cor") or "vermelho")
            )
            if cfg["saida"].get("imagem"):
                embed_saida.set_image(url=cfg["saida"]["imagem"])
            await canal.send(embed=embed_saida)
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
async def on_user_update(before, after):
    alteracoes = []
    if before.name != after.name:
        alteracoes.append(f"**Nome:** `{before.name}` → `{after.name}`")
    if before.global_name != after.global_name:
        alteracoes.append(f"**Nome de exibição:** `{before.global_name or before.name}` → `{after.global_name or after.name}`")
    if before.display_avatar.key != after.display_avatar.key:
        alteracoes.append("**Foto de perfil:** alterada")
    if not alteracoes:
        return
    descricao = f"**Usuário:** <@{after.id}> (`{after.id}`)\n" + "\n".join(alteracoes)
    if before.display_avatar.key != after.display_avatar.key:
        descricao += f"\n[Ver nova foto de perfil]({after.display_avatar.url})"
    for guild in bot.guilds:
        if guild.get_member(after.id):
            await enviar_log(guild, "👤 Perfil de membro atualizado", descricao, COR_INFO)

@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        antigo = before.nick or before.name
        novo = after.nick or after.name
        await enviar_log(
            after.guild,
            "👤 Nome de membro atualizado",
            f"**Membro:** {after.mention} (`{after.id}`)\n**Antes:** `{antigo}`\n**Depois:** `{novo}`",
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

# ---------- Moderação: comandos híbridos (prefixo v e slash) ----------
async def preparar_resposta_silenciosa(ctx):
    if ctx.interaction and not ctx.interaction.response.is_done():
        await ctx.defer(ephemeral=True)

async def finalizar_resposta_silenciosa(ctx):
    if ctx.interaction:
        try:
            await ctx.interaction.delete_original_response()
        except discord.HTTPException:
            pass

@bot.hybrid_command(name="banir", description="Bane um membro do servidor")
@app_commands.default_permissions(ban_members=True)
@commands.has_permissions(ban_members=True)
async def banir(ctx, membro: discord.Member, motivo: str = "Não informado"):
    if ctx.guild is None:
        return
    await preparar_resposta_silenciosa(ctx)
    try:
        await ctx.guild.ban(membro, reason=f"{motivo} | Aplicado por {ctx.author}")
        await finalizar_resposta_silenciosa(ctx)
    except discord.Forbidden:
        await ctx.send("❌ Não tenho permissão para banir esse membro.", delete_after=8)
    except discord.HTTPException:
        await ctx.send("❌ Não foi possível banir esse membro.", delete_after=8)

@bot.hybrid_command(name="expulsar", description="Expulsa um membro do servidor")
@app_commands.default_permissions(kick_members=True)
@commands.has_permissions(kick_members=True)
async def expulsar(ctx, membro: discord.Member, motivo: str = "Não informado"):
    if ctx.guild is None:
        return
    await preparar_resposta_silenciosa(ctx)
    try:
        await ctx.guild.kick(membro, reason=f"{motivo} | Aplicado por {ctx.author}")
        await finalizar_resposta_silenciosa(ctx)
    except discord.Forbidden:
        await ctx.send("❌ Não tenho permissão para expulsar esse membro.", delete_after=8)
    except discord.HTTPException:
        await ctx.send("❌ Não foi possível expulsar esse membro.", delete_after=8)

@bot.hybrid_command(name="mutar", description="Aplica timeout em um membro")
@app_commands.default_permissions(moderate_members=True)
@commands.has_permissions(moderate_members=True)
async def mutar(ctx, membro: discord.Member, minutos: app_commands.Range[int, 1, 40320] = 10, motivo: str = "Não informado"):
    if ctx.guild is None:
        return
    await preparar_resposta_silenciosa(ctx)
    try:
        await membro.timeout(discord.utils.utcnow() + timedelta(minutes=minutos), reason=f"{motivo} | Aplicado por {ctx.author}")
        await finalizar_resposta_silenciosa(ctx)
    except discord.Forbidden:
        await ctx.send("❌ Não tenho permissão para mutar esse membro.", delete_after=8)
    except discord.HTTPException:
        await ctx.send("❌ Não foi possível mutar esse membro.", delete_after=8)

@bot.hybrid_command(name="unban", description="Remove o banimento de um usuário pelo ID")
@app_commands.default_permissions(ban_members=True)
@commands.has_permissions(ban_members=True)
async def unban(ctx, usuario_id: str):
    if ctx.guild is None:
        return
    await preparar_resposta_silenciosa(ctx)
    try:
        user = await bot.fetch_user(int(usuario_id))
        await ctx.guild.unban(user, reason=f"Desbanido por {ctx.author}")
        await finalizar_resposta_silenciosa(ctx)
    except ValueError:
        await ctx.send("❌ Informe um ID de usuário válido.", delete_after=8)
    except discord.NotFound:
        await ctx.send("❌ Esse usuário não está banido.", delete_after=8)
    except discord.Forbidden:
        await ctx.send("❌ Não tenho permissão para desbanir usuários.", delete_after=8)
    except discord.HTTPException:
        await ctx.send("❌ Não foi possível desbanir esse usuário.", delete_after=8)

@bot.hybrid_command(name="desmutar", description="Remove o timeout de um membro")
@app_commands.default_permissions(moderate_members=True)
@commands.has_permissions(moderate_members=True)
async def desmutar(ctx, membro: discord.Member):
    if ctx.guild is None:
        return
    await preparar_resposta_silenciosa(ctx)
    try:
        await membro.timeout(None, reason=f"Timeout removido por {ctx.author}")
        await finalizar_resposta_silenciosa(ctx)
    except discord.Forbidden:
        await ctx.send("❌ Não tenho permissão para remover o timeout.", delete_after=8)
    except discord.HTTPException:
        await ctx.send("❌ Não foi possível desmutar esse membro.", delete_after=8)

@bot.hybrid_command(name="clear", description="Apaga mensagens do canal")
@app_commands.default_permissions(manage_messages=True)
@commands.has_permissions(manage_messages=True)
async def clear(ctx, quantidade: app_commands.Range[int, 1, 100] = 100):
    if ctx.guild is None:
        return
    try:
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)
        await ctx.channel.purge(limit=quantidade + (0 if ctx.interaction else 1), check=lambda m: not m.pinned)
        if ctx.interaction:
            await ctx.interaction.delete_original_response()
    except discord.Forbidden:
        if ctx.interaction:
            await ctx.followup.send("❌ Não tenho permissão para apagar mensagens.", ephemeral=True)
        else:
            await ctx.send("❌ Não tenho permissão para apagar mensagens.", delete_after=8)
    except discord.HTTPException:
        if ctx.interaction:
            await ctx.followup.send("❌ Não foi possível apagar as mensagens.", ephemeral=True)
        else:
            await ctx.send("❌ Não foi possível apagar as mensagens.", delete_after=8)

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
    mensagem="Texto principal do embed (opcional)",
    cor="Cor: nome ou #hex. Se vazio, fica amarelo",
    midia="Link de imagem (opcional)"
)
async def criar_embed(
    interaction: discord.Interaction,
    mensagem: str = None,
    cor: str = None,
    midia: str = None
):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        description=mensagem or "\u200b",
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
