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
from datetime import timedelta, datetime, timezone

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
    dados[gid]["ticket"].setdefault("rodape", "")
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

    # Painel independente de cargos por menu de seleção.
    painel_cargos = dados[gid].setdefault("painel_cargos", {})
    painel_cargos.setdefault("canal", None)
    painel_cargos.setdefault("mensagem", "")
    painel_cargos.setdefault("mensagem_embed", "")
    painel_cargos.setdefault("cargos", [])
    painel_cargos.setdefault("cor_embed", "#5865F2")
    painel_cargos.setdefault("cor_botoes", "cinza")
    painel_cargos.setdefault("rodape", "")
    painel_cargos.setdefault("modo", 1)
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


def ja_resgatou_daily(user_id, dados=None):
    """Retorna True somente se o usuário já registrou ao menos um Daily."""
    if dados is None:
        dados = carregar()
    conta = dados.get(str(user_id), {})
    return bool(conta.get("last_daily_date") or conta.get("last_daily", 0))

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
    """Apresenta o estado sem indicadores coloridos, mantendo o padrão formal."""
    return "Ativo" if ativo else "Desativado"

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
intents.invites = True
bot = commands.Bot(
    command_prefix=["v", "V"],
    intents=intents
)

# Cache local dos convites para identificar quem trouxe cada novo membro.
convites_cache = {}


async def atualizar_cache_convites(guild):
    """Atualiza os usos dos convites; requer permissão para gerenciar convites."""
    try:
        convites = await guild.invites()
        convites_cache[guild.id] = {
            convite.code: convite.uses or 0 for convite in convites
        }
    except (discord.Forbidden, discord.HTTPException) as erro:
        print(f"Não foi possível consultar convites de {guild.name}: {erro}")
        convites_cache.pop(guild.id, None)


# ============================================================
#  EMBEDS DO PAINEL CONFIGURAR - ORGANIZADOS
# ============================================================
def embed_painel_principal(guild, guild_id):
    cfg = get_guild_config(guild_id)
    e = discord.Embed(
        title="⚙️ Central de Configuração",
        description=(
            "Gerencie os recursos e as funcionalidades do Ratinho neste servidor.\n"
            "Selecione uma das categorias disponíveis para consultar informações "
            "e administrar suas respectivas configurações."
        ),
        color=COR_PRINCIPAL
    )
    if guild.icon:
        e.set_thumbnail(url=guild.icon.url)

    v_logs = (
        f"▸ **Situação:** {status_txt(cfg['logs']['ativo'])}\n\n"
        f"▸ **Canal de registro:** {canal_txt(cfg['logs']['canal'])}\n\n"
        "▸ **Finalidade:** registrar atividades e eventos relevantes do servidor."
    )
    e.add_field(name="📋  Registro de eventos", value=v_logs, inline=False)

    v_ticket = (
        f"▸ **Canal do painel:** {canal_txt(cfg['ticket']['canal_painel'])}\n\n"
        f"▸ **Tipos de atendimento:** {len(cfg['ticket'].get('botoes', []))} configurado(s)"
    )
    e.add_field(name="🎫  Sistema de tickets", value=v_ticket, inline=False)

    v_ent = (
        f"▸ **Situação:** {status_txt(cfg['entrada']['ativo'])}\n\n"
        f"▸ **Canal de publicação:** {canal_txt(cfg['entrada']['canal'])}\n\n"
        "▸ **Finalidade:** publicar uma notificação sempre que um membro ingressar no servidor."
    )
    e.add_field(name="👋  Mensagens de entrada", value=v_ent, inline=False)

    v_sai = (
        f"▸ **Situação:** {status_txt(cfg['saida']['ativo'])}\n\n"
        f"▸ **Canal de publicação:** {canal_txt(cfg['saida']['canal'])}\n\n"
        "▸ **Finalidade:** publicar uma notificação sempre que um membro deixar o servidor."
    )
    e.add_field(name="🚪  Mensagens de saída", value=v_sai, inline=False)
    e.set_footer(text=f"{guild.name}  •  Administração do Ratinho")
    return e


def embed_logs(guild_id):
    cfg = get_guild_config(guild_id)["logs"]
    e = discord.Embed(
        title="📋 Registro de eventos",
        description=(
            "Ajuste o registro de atividades do servidor.\n"
            "Use os controles abaixo para alterar as configurações."
        ),
        color=COR_PRINCIPAL
    )
    e.add_field(name="◈ Status", value=status_txt(cfg["ativo"]), inline=True)
    e.add_field(name="◈ Canal de registro", value=canal_txt(cfg["canal"]), inline=True)
    e.add_field(
        name="▸ Eventos registrados",
        value=(
            "▫ Mensagens apagadas ou editadas\n"
            "▫ Membros que entram ou saem\n"
            "▫ Membros banidos ou desbanidos"
        ),
        inline=False
    )
    e.set_footer(text="Registro de eventos  •  Ratinho")
    return e


def embed_ticket(guild_id):
    cfg = get_guild_config(guild_id)["ticket"]
    botoes = cfg.get("botoes", [])
    resumo = "\n".join(
        f"▫ **{b['nome']}**  ·  {b.get('cor', 'azul')}  ·  {cargo_txt(b.get('cargo_suporte'))}"
        for b in botoes
    ) or "`Nenhum botão criado`"
    e = discord.Embed(
        title="🎫 Configuração de tickets",
        description=(
            "Gerencie o painel de atendimento e os tipos de ticket.\n"
            "Cada botão pode ter sua própria cor e cargo responsável."
        ),
        color=parse_cor(cfg.get("cor") or "amarelo")
    )
    e.add_field(name="◈ Canal do painel", value=canal_txt(cfg.get("canal_painel")), inline=True)
    e.add_field(name="◈ Categoria dos tickets", value=canal_txt(cfg.get("categoria")), inline=True)
    e.add_field(name=f"▸ Botões configurados · {len(botoes)}", value=resumo[:1024], inline=False)
    e.add_field(name="▸ Mensagem exibida no painel", value=cfg.get("mensagem", "")[:1000] or "`Não definida`", inline=False)
    e.set_footer(text="Tickets  •  Ratinho")
    return e


def embed_entrada_saida(guild_id, tipo):
    cfg = get_guild_config(guild_id)[tipo]
    is_entrada = tipo == "entrada"
    if is_entrada:
        titulo = "👋 Mensagens de entrada"
        desc = "Configure o aviso enviado quando um membro entra no servidor."
    else:
        titulo = "🚪 Mensagens de saída"
        desc = "Configure o aviso enviado quando um membro sai do servidor."
    e = discord.Embed(
        title=titulo,
        description=desc,
        color=parse_cor(cfg.get("cor") or ("verde" if is_entrada else "vermelho"))
    )
    if cfg.get("imagem"):
        e.set_image(url=cfg["imagem"])
    e.add_field(name="◈ Status", value=status_txt(cfg["ativo"]), inline=True)
    e.add_field(name="◈ Canal", value=canal_txt(cfg["canal"]), inline=True)
    e.add_field(
        name="▸ Mensagem configurada",
        value=cfg["mensagem"][:1000] or "`Nenhuma mensagem definida`",
        inline=False
    )
    e.add_field(
        name="▸ Variáveis que você pode usar",
        value=(
            "▫ `{user}`  ·  menciona o membro\n"
            "▫ `{nome}`  ·  nome do membro\n"
            "▫ `{server}`  ·  nome do servidor\n"
            "▫ `{membros}`  ·  total de membros"
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

class ModalRodapeTicket(discord.ui.Modal):
    def __init__(self, guild_id):
        super().__init__(title="Personalizar rodapé do painel")
        self.guild_id = guild_id
        atual = get_guild_config(guild_id)["ticket"].get("rodape", "")
        self.rodape = discord.ui.TextInput(
            label="Texto do rodapé (opcional)",
            placeholder="Deixe vazio para não exibir rodapé",
            default=atual,
            required=False,
            max_length=2048
        )
        self.add_item(self.rodape)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = get_guild_config(self.guild_id)
        cfg["ticket"]["rodape"] = self.rodape.value.strip()
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message(
            "✅ Rodapé salvo! Se deixar vazio, nenhum rodapé será exibido.",
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
        self.add_item(self.cor)
        # Tickets não oferecem mais configuração de imagem.
        if self.tipo != "ticket":
            self.imagem = discord.ui.TextInput(
                label="URL da imagem (deixe vazio para remover)",
                placeholder="https://...",
                default=str(cfg.get("imagem") or ""),
                required=False,
                max_length=400
            )
            self.add_item(self.imagem)

    async def on_submit(self, interaction: discord.Interaction):
        cor = self.cor.value.strip() or "amarelo"
        cfg = get_guild_config(self.guild_id)
        cfg[self.tipo]["cor"] = cor
        if self.tipo != "ticket":
            imagem = self.imagem.value.strip() or None
            if imagem and not imagem.lower().startswith(("https://", "http://")):
                await interaction.response.send_message(
                    "❌ A imagem precisa ser um link HTTP ou HTTPS válido.",
                    ephemeral=True
                )
                return
            cfg[self.tipo]["imagem"] = imagem
        update_guild_config(self.guild_id, cfg)
        await interaction.response.send_message(
            "✅ Aparência salva com sucesso!",
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
        elif self.destino == "painel_cargos":
            cfg["painel_cargos"]["canal"] = int(canal)
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
                await interaction.response.send_message("❌ O Discord permite no máximo 25 opções no menu de tickets.", ephemeral=True)
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
            "O que deseja fazer com essa opção?",
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

    @discord.ui.button(label="Personalizar rodapé", style=discord.ButtonStyle.secondary, emoji="📝", row=1)
    async def personalizar_rodape(self, interaction, button):
        await interaction.response.send_modal(ModalRodapeTicket(self.guild_id))

    @discord.ui.button(label="Adicionar opção", style=discord.ButtonStyle.secondary, emoji="➕", row=1)
    async def adicionar(self, interaction, button):
        await interaction.response.send_modal(ModalBotaoTicket(self.guild_id))

    @discord.ui.button(label="Gerenciar opções", style=discord.ButtonStyle.secondary, emoji="🛠️", row=1)
    async def gerenciar(self, interaction, button):
        if not get_guild_config(self.guild_id)["ticket"].get("botoes"):
            await interaction.response.send_message("Você ainda não criou opções de ticket.", ephemeral=True)
            return
        await interaction.response.send_message("Selecione uma opção para editar, trocar o cargo responsável ou excluir:", view=SelectGerenciarBotaoTicketView(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Enviar Painel", style=discord.ButtonStyle.secondary, emoji="📤", row=2)
    async def enviar(self, interaction, button):
        cfg = get_guild_config(self.guild_id)["ticket"]
        if not cfg.get("canal_painel"):
            await interaction.response.send_message("❌ Defina o canal do painel primeiro!", ephemeral=True)
            return
        if not cfg.get("botoes"):
            await interaction.response.send_message("❌ Crie pelo menos uma opção antes de enviar o painel.", ephemeral=True)
            return
        canal = interaction.guild.get_channel(cfg["canal_painel"])
        if not canal:
            await interaction.response.send_message("❌ Canal não encontrado!", ephemeral=True)
            return
        embed = discord.Embed(description=cfg["mensagem"], color=parse_cor(cfg.get("cor")))
        if cfg.get("rodape"):
            embed.set_footer(text=cfg["rodape"])
        await canal.send(embed=embed, view=TicketAbrirView(self.guild_id))
        await interaction.response.send_message(f"✅ Painel enviado em {canal.mention}!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=3)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_painel_principal(interaction.guild, self.guild_id), view=PainelConfigView(self.guild_id))


# ============================================================
#  PAINEL DE CARGOS POR MENU DE SELEÇÃO
# ============================================================
def embed_config_painel_cargos(guild_id):
    cfg = get_guild_config(guild_id)["painel_cargos"]
    modos = {
        1: "Vários cargos (adicionar/remover individualmente)",
        2: "Apenas um cargo (troca ao selecionar outro)",
        3: "Apenas retirar cargos"
    }
    canal = f"<#{cfg['canal']}>" if cfg.get("canal") else "Não definido"
    cargos = cfg.get("cargos", [])
    e = discord.Embed(
        title="🎨 Configuração do painel de cargos",
        description=(
            "Personalize o painel que permite aos membros escolherem seus cargos.\n"
            "Configure as opções abaixo e, quando terminar, publique o painel."
        ),
        color=parse_cor(cfg.get("cor_embed"))
    )
    e.add_field(name="📢 Canal do painel", value=canal, inline=True)
    e.add_field(name="🎭 Cargos cadastrados", value=str(len(cargos)), inline=True)
    e.add_field(name="⚙️ Modo de funcionamento", value=modos.get(int(cfg.get("modo", 1)), modos[1]), inline=False)
    e.add_field(name="📝 Mensagem fora da embed", value="Configurada" if cfg.get("mensagem") else "Vazia", inline=True)
    e.add_field(name="🖼️ Mensagem da embed", value="Configurada" if cfg.get("mensagem_embed") else "Vazia", inline=True)
    e.add_field(name="🔻 Rodapé", value=cfg.get("rodape") or "Não definido", inline=False)
    e.set_footer(text="As alterações são salvas automaticamente.")
    return e


class ModalTextoPainelCargos(discord.ui.Modal):
    def __init__(self, guild_id, campo):
        titulos = {
            "mensagem": "Mensagem fora da embed",
            "mensagem_embed": "Mensagem dentro da embed",
            "rodape": "Personalizar rodapé"
        }
        super().__init__(title=titulos[campo])
        self.guild_id = guild_id
        self.campo = campo
        cfg = get_guild_config(guild_id)["painel_cargos"]
        labels = {
            "mensagem": "Texto enviado acima da embed",
            "mensagem_embed": "Texto exibido dentro da embed",
            "rodape": "Texto do rodapé (opcional)"
        }
        self.texto = discord.ui.TextInput(
            label=labels[campo],
            style=discord.TextStyle.paragraph,
            default=cfg.get(campo, "") or None,
            placeholder="Digite o texto aqui...",
            required=False,
            max_length=2000 if campo != "mensagem_embed" else 4000
        )
        self.add_item(self.texto)

    async def on_submit(self, interaction: discord.Interaction):
        dados = get_guild_config(self.guild_id)
        dados["painel_cargos"][self.campo] = self.texto.value.strip()
        update_guild_config(self.guild_id, dados)
        await interaction.response.send_message("✅ Texto salvo com sucesso!", ephemeral=True)


class ModalCorPainelCargos(discord.ui.Modal):
    def __init__(self, guild_id):
        super().__init__(title="Cor da embed")
        self.guild_id = guild_id
        atual = get_guild_config(guild_id)["painel_cargos"].get("cor_embed", "#5865F2")
        self.cor = discord.ui.TextInput(
            label="Nome da cor ou hexadecimal",
            placeholder="Ex.: roxo, azul ou #5865F2",
            default=str(atual),
            max_length=20
        )
        self.add_item(self.cor)

    async def on_submit(self, interaction: discord.Interaction):
        valor = self.cor.value.strip()
        # parse_cor aceita nomes conhecidos e hexadecimal; valida o hexadecimal aqui.
        limpo = valor.lower().replace("#", "").replace("0x", "")
        nomes = {"amarelo", "vermelho", "verde", "azul", "roxo", "rosa", "laranja", "preto", "branco", "cinza", "ciano"}
        if valor.lower() not in nomes:
            try:
                numero = int(limpo, 16)
                if not 0 <= numero <= 0xFFFFFF:
                    raise ValueError
            except Exception:
                await interaction.response.send_message("❌ Cor inválida. Use um nome conhecido ou hexadecimal, como `#5865F2`.", ephemeral=True)
                return
        dados = get_guild_config(self.guild_id)
        dados["painel_cargos"]["cor_embed"] = valor
        update_guild_config(self.guild_id, dados)
        await interaction.response.send_message("✅ Cor da embed salva!", ephemeral=True)


class ModalCorBotoesPainelCargos(discord.ui.Modal):
    def __init__(self, guild_id):
        super().__init__(title="Cor dos botões")
        self.guild_id = guild_id
        atual = get_guild_config(guild_id)["painel_cargos"].get("cor_botoes", "cinza")
        self.cor = discord.ui.TextInput(
            label="Cor (azul, verde, vermelho ou cinza)",
            placeholder="Ex.: cinza",
            default=str(atual),
            max_length=20
        )
        self.add_item(self.cor)

    async def on_submit(self, interaction: discord.Interaction):
        valor = self.cor.value.strip().lower()
        if valor not in {"azul", "verde", "vermelho", "cinza"}:
            await interaction.response.send_message("❌ Escolha azul, verde, vermelho ou cinza.", ephemeral=True)
            return
        dados = get_guild_config(self.guild_id)
        dados["painel_cargos"]["cor_botoes"] = valor
        update_guild_config(self.guild_id, dados)
        await interaction.response.send_message(
            "✅ Preferência salva. **Observação:** o menu de seleção do Discord tem aparência e cor controladas pelo próprio Discord; essa cor não altera o menu. Ela fica registrada caso o painel seja convertido para botões individuais.",
            ephemeral=True
        )


class AdicionarCargosPainelView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        seletor = discord.ui.RoleSelect(
            placeholder="Selecione até 25 cargos para o painel",
            min_values=1,
            max_values=25
        )
        seletor.callback = self.salvar
        self.add_item(seletor)

    async def salvar(self, interaction: discord.Interaction):
        dados = get_guild_config(self.guild_id)
        painel = dados["painel_cargos"]
        atuais = [int(x) for x in painel.get("cargos", [])]
        adicionados = []
        for valor in interaction.data.get("values", []):
            rid = int(valor)
            if rid not in atuais:
                atuais.append(rid)
                adicionados.append(rid)
        painel["cargos"] = atuais[:25]
        update_guild_config(self.guild_id, dados)
        nomes = [interaction.guild.get_role(rid).name for rid in adicionados if interaction.guild.get_role(rid)]
        resumo = ", ".join(nomes) if nomes else "Nenhum cargo novo foi adicionado."
        await interaction.response.send_message(f"✅ Cargos atualizados: {resumo}", ephemeral=True)


class RemoverCargosPainelView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        ids = get_guild_config(guild_id)["painel_cargos"].get("cargos", [])
        seletor = discord.ui.RoleSelect(
            placeholder="Selecione os cargos que deseja remover do painel",
            min_values=1,
            max_values=max(1, min(25, len(ids)))
        )
        seletor.callback = self.remover
        self.add_item(seletor)

    async def remover(self, interaction: discord.Interaction):
        dados = get_guild_config(self.guild_id)
        removidos = {int(x) for x in interaction.data.get("values", [])}
        dados["painel_cargos"]["cargos"] = [int(x) for x in dados["painel_cargos"].get("cargos", []) if int(x) not in removidos]
        update_guild_config(self.guild_id, dados)
        await interaction.response.send_message("✅ Cargos removidos da configuração do painel.", ephemeral=True)


class GerenciarCargosPainelView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id

    @discord.ui.button(label="Adicionar cargos", style=discord.ButtonStyle.secondary, emoji="➕")
    async def adicionar(self, interaction, button):
        await interaction.response.send_message("Selecione os cargos que deseja adicionar:", view=AdicionarCargosPainelView(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Remover cargos", style=discord.ButtonStyle.secondary, emoji="➖")
    async def remover(self, interaction, button):
        if not get_guild_config(self.guild_id)["painel_cargos"].get("cargos"):
            await interaction.response.send_message("Ainda não há cargos cadastrados.", ephemeral=True)
            return
        await interaction.response.send_message("Selecione os cargos que deseja retirar da configuração:", view=RemoverCargosPainelView(self.guild_id), ephemeral=True)


class ModoPainelCargosSelect(discord.ui.Select):
    def __init__(self, guild_id):
        self.guild_id = guild_id
        atual = int(get_guild_config(guild_id)["painel_cargos"].get("modo", 1))
        opcoes = [
            discord.SelectOption(label="Vários cargos", value="1", description="Pode manter vários cargos ao mesmo tempo.", default=atual == 1),
            discord.SelectOption(label="Apenas um cargo", value="2", description="Troca o cargo atual pelo novo; clicar de novo remove.", default=atual == 2),
            discord.SelectOption(label="Apenas tirar cargos", value="3", description="O menu só remove cargos que a pessoa já possui.", default=atual == 3)
        ]
        super().__init__(placeholder="Escolha o modo de funcionamento", min_values=1, max_values=1, options=opcoes)

    async def callback(self, interaction: discord.Interaction):
        dados = get_guild_config(self.guild_id)
        dados["painel_cargos"]["modo"] = int(self.values[0])
        update_guild_config(self.guild_id, dados)
        await interaction.response.send_message("✅ Modo de funcionamento atualizado!", ephemeral=True)


class ModoPainelCargosView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.add_item(ModoPainelCargosSelect(guild_id))


class PainelCargosConfigView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=600)
        self.guild_id = guild_id

    @discord.ui.button(label="Canal do painel", style=discord.ButtonStyle.secondary, emoji="📢", row=0)
    async def canal(self, interaction, button):
        await interaction.response.send_message("Selecione onde o painel será publicado:", view=SelectCanalView(self.guild_id, "painel_cargos"), ephemeral=True)

    @discord.ui.button(label="Mensagem (opcional)", style=discord.ButtonStyle.secondary, emoji="💬", row=0)
    async def mensagem(self, interaction, button):
        await interaction.response.send_modal(ModalTextoPainelCargos(self.guild_id, "mensagem"))

    @discord.ui.button(label="Mensagem Embed (opcional)", style=discord.ButtonStyle.secondary, emoji="🖼️", row=0)
    async def mensagem_embed(self, interaction, button):
        await interaction.response.send_modal(ModalTextoPainelCargos(self.guild_id, "mensagem_embed"))

    @discord.ui.button(label="Cargos e seus botões", style=discord.ButtonStyle.secondary, emoji="🎭", row=1)
    async def cargos(self, interaction, button):
        await interaction.response.send_message("Gerencie os cargos disponíveis no menu de seleção:", view=GerenciarCargosPainelView(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Cor dos botões", style=discord.ButtonStyle.secondary, emoji="🎨", row=1)
    async def cor_botoes(self, interaction, button):
        await interaction.response.send_modal(ModalCorBotoesPainelCargos(self.guild_id))

    @discord.ui.button(label="Cor da embed", style=discord.ButtonStyle.secondary, emoji="🌈", row=1)
    async def cor_embed(self, interaction, button):
        await interaction.response.send_modal(ModalCorPainelCargos(self.guild_id))

    @discord.ui.button(label="Rodapé", style=discord.ButtonStyle.secondary, emoji="📝", row=2)
    async def rodape(self, interaction, button):
        await interaction.response.send_modal(ModalTextoPainelCargos(self.guild_id, "rodape"))

    @discord.ui.button(label="Modo", style=discord.ButtonStyle.secondary, emoji="⚙️", row=2)
    async def modo(self, interaction, button):
        await interaction.response.send_message("Escolha como os cargos serão entregues:", view=ModoPainelCargosView(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Publicar painel", style=discord.ButtonStyle.secondary, emoji="📤", row=3)
    async def publicar(self, interaction, button):
        cfg = get_guild_config(self.guild_id)["painel_cargos"]
        if not cfg.get("canal"):
            await interaction.response.send_message("❌ Defina o canal do painel primeiro.", ephemeral=True)
            return
        ids = [int(x) for x in cfg.get("cargos", [])]
        ids_validos = [rid for rid in ids if interaction.guild.get_role(rid)]
        if not ids_validos:
            await interaction.response.send_message("❌ Cadastre pelo menos um cargo antes de publicar.", ephemeral=True)
            return
        if len(ids_validos) > 25:
            await interaction.response.send_message("❌ O painel aceita no máximo 25 cargos.", ephemeral=True)
            return
        canal = interaction.guild.get_channel(int(cfg["canal"]))
        if not canal:
            await interaction.response.send_message("❌ O canal configurado não foi encontrado.", ephemeral=True)
            return
        embed = discord.Embed(description=cfg.get("mensagem_embed") or None, color=parse_cor(cfg.get("cor_embed")))
        if cfg.get("rodape"):
            embed.set_footer(text=cfg["rodape"][:2048])
        try:
            await canal.send(content=cfg.get("mensagem") or None, embed=embed, view=PainelCargosPublicoView(self.guild_id))
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para enviar mensagens ou embeds nesse canal.", ephemeral=True)
            return
        except discord.HTTPException as erro:
            await interaction.response.send_message(f"❌ O Discord não aceitou o painel: {erro}", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Painel de cargos publicado em {canal.mention}!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️", row=3)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_painel_principal(interaction.guild, self.guild_id), view=PainelConfigView(self.guild_id))


class PainelCargosSelect(discord.ui.Select):
    def __init__(self, guild_id, role_ids, menu_numero):
        self.guild_id = guild_id
        opcoes = []
        guild = bot.get_guild(guild_id)
        for rid in role_ids:
            cargo = guild.get_role(int(rid)) if guild else None
            if cargo and not cargo.is_default() and not cargo.managed:
                opcoes.append(discord.SelectOption(label=cargo.name[:100], value=str(cargo.id)))
        if not opcoes:
            return
        super().__init__(
            placeholder="Faça uma seleção" if menu_numero == 1 else "Faça uma seleção (continuação)",
            min_values=1,
            max_values=1,
            options=opcoes,
            custom_id=f"ratinho_painel_cargos:{guild_id}:{menu_numero}"
        )

    async def callback(self, interaction: discord.Interaction):
        await processar_selecao_cargo(interaction, self.guild_id, int(self.values[0]))


class PainelCargosPublicoView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        cfg = get_guild_config(guild_id)["painel_cargos"]
        guild = bot.get_guild(guild_id)
        ids_validos = []
        for rid in cfg.get("cargos", [])[:25]:
            try:
                cargo = guild.get_role(int(rid)) if guild else None
            except (TypeError, ValueError):
                cargo = None
            if cargo and not cargo.is_default() and not cargo.managed:
                ids_validos.append(cargo.id)

        if ids_validos:
            # Um único menu de seleção, com no máximo 25 opções.
            self.add_item(PainelCargosSelect(guild_id, ids_validos, 1))


async def processar_selecao_cargo(interaction, guild_id, role_id):
    if interaction.guild_id != guild_id:
        await interaction.response.send_message("❌ Este painel pertence a outro servidor.", ephemeral=True)
        return

    cfg = get_guild_config(guild_id)["painel_cargos"]
    roles = [interaction.guild.get_role(int(rid)) for rid in cfg.get("cargos", [])]
    roles = [r for r in roles if r and not r.is_default() and not r.managed]

    if role_id == 0:
        await interaction.response.send_message(
            "❌ Este painel não possui cargos válidos. Peça a um administrador para configurá-lo novamente.",
            ephemeral=True
        )
        return

    escolhido = interaction.guild.get_role(role_id)
    if not escolhido or escolhido not in roles:
        await interaction.response.send_message(
            "❌ Esse cargo não está mais disponível no painel.",
            ephemeral=True
        )
        return

    membro = interaction.user
    modo = int(cfg.get("modo", 1))
    possui = escolhido in membro.roles
    bot_membro = interaction.guild.me

    if not bot_membro or not bot_membro.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ Preciso da permissão **Gerenciar cargos** para entregar os cargos.",
            ephemeral=True
        )
        return

    if escolhido >= bot_membro.top_role:
        await interaction.response.send_message(
            "❌ Meu cargo mais alto precisa ficar acima do cargo selecionado.",
            ephemeral=True
        )
        return

    # Confirma a interação antes de chamar a API do Discord para alterar cargos.
    # Isso evita o erro "Esta interação não respondeu" quando a API demora.
    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        if modo == 3:
            if not possui:
                resposta = "ℹ️ Você não possui esse cargo, então não há nada para retirar."
            else:
                await membro.remove_roles(escolhido, reason="Painel de cargos do Ratinho")
                resposta = f"➖ O cargo {escolhido.mention} foi retirado."

        elif modo == 2:
            if possui:
                await membro.remove_roles(escolhido, reason="Cargo removido pelo painel do Ratinho")
                resposta = f"➖ O cargo {escolhido.mention} foi retirado."
            else:
                retirar = [
                    r for r in roles
                    if r in membro.roles and r != escolhido and r < bot_membro.top_role
                ]
                if retirar:
                    await membro.remove_roles(
                        *retirar,
                        reason="Troca de cargo pelo painel do Ratinho"
                    )
                await membro.add_roles(
                    escolhido,
                    reason="Cargo escolhido no painel do Ratinho"
                )
                resposta = f"✅ Seu cargo foi alterado para {escolhido.mention}."

        else:
            if possui:
                await membro.remove_roles(escolhido, reason="Cargo removido pelo painel do Ratinho")
                resposta = f"➖ O cargo {escolhido.mention} foi retirado."
            else:
                await membro.add_roles(escolhido, reason="Cargo escolhido no painel do Ratinho")
                resposta = f"✅ Você recebeu o cargo {escolhido.mention}!"

        await interaction.followup.send(resposta, ephemeral=True)

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Não consegui alterar esse cargo. Confira a hierarquia dos cargos e minhas permissões.",
            ephemeral=True
        )
    except discord.HTTPException:
        await interaction.followup.send(
            "❌ O Discord não conseguiu atualizar seu cargo. Tente novamente.",
            ephemeral=True
        )
    except Exception as erro:
        print(f"Erro ao processar seleção de cargo: {erro}")
        await interaction.followup.send(
            "❌ Ocorreu um erro inesperado ao alterar seu cargo. Avise a equipe do servidor.",
            ephemeral=True
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


class TicketTipoSelect(discord.ui.Select):
    def __init__(self, guild_id, tipos):
        self.guild_id = guild_id
        opcoes = [
            discord.SelectOption(
                label=str(dados.get("nome", "Ticket"))[:100],
                value=str(dados["id"]),
                description=f"Abrir atendimento: {str(dados.get('nome', 'Ticket'))[:80]}"[:100]
            )
            for dados in tipos[:25]
        ]
        super().__init__(
            placeholder="Faça uma seleção",
            min_values=1,
            max_values=1,
            options=opcoes,
            custom_id=f"ratinho_ticket_select:{guild_id}"
        )

    async def callback(self, interaction):
        await abrir_ticket_tipo(interaction, self.values[0])


class TicketAbrirView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        tipos = get_guild_config(guild_id)["ticket"].get("botoes", [])[:25]
        if tipos:
            self.add_item(TicketTipoSelect(guild_id, tipos))


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
            painel_cfg = get_guild_config(guild.id)["painel_cargos"]
            if painel_cfg.get("cargos"):
                bot.add_view(PainelCargosPublicoView(guild.id))
        except Exception as e:
            print(f"Erro ao registrar painel de cargos de {guild.id}: {e}")
        await atualizar_cache_convites(guild)
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
    await atualizar_cache_convites(guild)
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
async def on_invite_create(invite):
    convites_cache.setdefault(invite.guild.id, {})[invite.code] = invite.uses or 0


@bot.event
async def on_invite_delete(invite):
    convites_cache.setdefault(invite.guild.id, {}).pop(invite.code, None)


@bot.event
async def on_member_join(member):
    convite_usado = None
    try:
        convites_atuais = await member.guild.invites()
        cache_anterior = convites_cache.get(member.guild.id, {})
        for convite in convites_atuais:
            if (convite.uses or 0) > cache_anterior.get(convite.code, 0):
                convite_usado = convite
                break
        convites_cache[member.guild.id] = {
            convite.code: convite.uses or 0 for convite in convites_atuais
        }
    except (discord.Forbidden, discord.HTTPException) as erro:
        print(f"Não foi possível identificar o convite usado em {member.guild.name}: {erro}")

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
            f"<t:{int(member.created_at.timestamp())}:R>\n"
            + (
                f"Convidado por: {convite_usado.inviter.mention} "
                f"(`{convite_usado.inviter.id}`) · Convite: `{convite_usado.code}`"
                if convite_usado and convite_usado.inviter
                else "Convite utilizado: não identificado"
            )
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
    # Executa comandos prefixados após correção da mensagem por edição.
    await bot.process_commands(after)

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

class PainelRankVolts(discord.ui.View):
    def __init__(self, guild, solicitante):
        super().__init__(timeout=300)
        self.guild = guild
        self.solicitante = solicitante

    async def criar_embed_global(self):
        dados = carregar()
        contas = []
        for uid, conta in dados.items():
            try:
                saldo = int(conta.get("volts", 0))
                user_id = int(uid)
            except (TypeError, ValueError, AttributeError):
                continue
            if saldo > 0:
                contas.append((user_id, saldo))

        contas.sort(key=lambda item: item[1], reverse=True)
        contas = contas[:10]

        embed = discord.Embed(
            title="🌎 Ranking Global de Volts",
            description=(
                "Os **10 usuários** com mais Volts no banco global do Ratinho.\n"
                "O saldo é compartilhado entre os servidores."
            ),
            color=COR_PRINCIPAL,
            timestamp=discord.utils.utcnow()
        )

        if not contas:
            embed.description += "\n\nAinda não há usuários com Volts registrados."
            return embed

        linhas = []
        medalhas = ["🥇", "🥈", "🥉"]
        membros_cache = {}
        for guild in bot.guilds:
            for membro in guild.members:
                membros_cache[membro.id] = membro

        for posicao, (user_id, saldo) in enumerate(contas, start=1):
            usuario = membros_cache.get(user_id) or bot.get_user(user_id)
            if usuario is None:
                try:
                    usuario = await bot.fetch_user(user_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    usuario = None
            nome = usuario.display_name if isinstance(usuario, discord.Member) else (usuario.name if usuario else f"Usuário {user_id}")
            medalha = medalhas[posicao - 1] if posicao <= 3 else f"**{posicao}.**"
            linhas.append(f"{medalha} **{discord.utils.escape_markdown(nome)}** — {fmt_volts(saldo)}")

        embed.add_field(name="Classificação", value="\n".join(linhas), inline=False)
        embed.set_footer(text=f"Solicitado por {self.solicitante.display_name} • Ranking global")
        return embed

    def criar_embed_local(self):
        dados = carregar()
        contas = []
        for membro in self.guild.members:
            if membro.bot:
                continue
            conta = dados.get(str(membro.id), {})
            try:
                saldo = int(conta.get("volts", 0))
            except (TypeError, ValueError, AttributeError):
                saldo = 0
            if saldo > 0:
                contas.append((membro, saldo))

        contas.sort(key=lambda item: item[1], reverse=True)
        contas = contas[:10]
        embed = discord.Embed(
            title=f"🏠 Ranking de Volts — {self.guild.name}",
            description="Os **10 usuários** com mais Volts neste servidor.",
            color=COR_PRINCIPAL,
            timestamp=discord.utils.utcnow()
        )

        if not contas:
            embed.description += "\n\nAinda não há membros com Volts registrados neste servidor."
        else:
            linhas = []
            medalhas = ["🥇", "🥈", "🥉"]
            for posicao, (membro, saldo) in enumerate(contas, start=1):
                medalha = medalhas[posicao - 1] if posicao <= 3 else f"**{posicao}.**"
                linhas.append(f"{medalha} **{discord.utils.escape_markdown(membro.display_name)}** — {fmt_volts(saldo)}")
            embed.add_field(name="Classificação", value="\n".join(linhas), inline=False)

        embed.set_thumbnail(url=self.guild.icon.url if self.guild.icon else self.solicitante.display_avatar.url)
        embed.set_footer(text=f"Solicitado por {self.solicitante.display_name} • Ranking local")
        return embed

    @discord.ui.button(label="Global", emoji="🌎", style=discord.ButtonStyle.primary)
    async def global_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self.criar_embed_global()
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Local", emoji="🏠", style=discord.ButtonStyle.secondary)
    async def local_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.criar_embed_local()
        await interaction.response.edit_message(embed=embed, view=self)



# ---------- BLACKJACK ----------
def bj_valor_carta(carta):
    return 11 if carta == 1 else min(carta, 10)

def bj_total(mao):
    total = sum(bj_valor_carta(c) for c in mao)
    ases = mao.count(1)
    while total > 21 and ases:
        total -= 10
        ases -= 1
    return total

def bj_comprar():
    return random.randint(1, 13)

def bj_nome_carta(carta):
    # O Ás pode valer 1 ou 11 no Blackjack.
    if carta == 1:
        return "1/11"
    return str(10 if carta >= 10 else carta)

def bj_mostrar_mao(mao):
    # Mostra as duas possibilidades do total quando há Ás:
    # primeiro o total contando o Ás como 11, depois como 1.
    total_alto = sum(bj_valor_carta(c) for c in mao)
    total_baixo = total_alto - (10 * mao.count(1))

    if mao.count(1):
        if total_alto > 21 and total_baixo <= 21:
            total_formatado = f"(~~{total_alto}~~/{total_baixo})"
        elif total_baixo > 21:
            total_formatado = f"(~~{total_alto}/{total_baixo}~~)"
        else:
            total_formatado = f"({total_alto}/{total_baixo})"
    else:
        total_formatado = f"~~({total_baixo})~~" if total_baixo > 21 else f"({total_baixo})"

    return " · ".join(bj_nome_carta(c) for c in mao) + f"  {total_formatado}"

def bj_parse_valor(texto):
    if texto is None:
        return 0
    texto = texto.strip().lower().replace(".", "").replace(",", "")
    multiplicador = 1
    if texto.endswith("k"):
        multiplicador = 1_000
        texto = texto[:-1]
    elif texto.endswith("m"):
        multiplicador = 1_000_000
        texto = texto[:-1]
    if not texto.isdigit():
        raise ValueError
    return int(texto) * multiplicador


def bj_proxima_partida():
    """Incrementa um contador persistente de partidas, inclusive após reinícios."""
    if UPSTASH_URL and UPSTASH_TOKEN:
        try:
            req = urllib.request.Request(
                f"{UPSTASH_URL.rstrip('/')}/incr/blackjack_counter",
                headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read())
            numero = data.get("result")
            if isinstance(numero, int):
                return numero
            raise ValueError("Resposta inválida do contador no Upstash")
        except Exception as e:
            print(f"Erro ao incrementar contador do Blackjack no Upstash: {e}")

    arquivo = "blackjack_counter.json"
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
        atual = int(dados.get("total", 0))
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        atual = 0

    proximo = atual + 1
    try:
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump({"total": proximo}, f)
    except OSError as e:
        print(f"Erro ao salvar contador local do Blackjack: {e}")
    return proximo


class BlackjackDesafio(discord.ui.View):
    def __init__(self, desafiante, adversario, aposta):
        super().__init__(timeout=60)
        self.desafiante = desafiante
        self.adversario = adversario
        self.aposta = aposta
        self.message = None

    @discord.ui.button(label="Aceitar", emoji="✅", style=discord.ButtonStyle.secondary)
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.adversario.id:
            await interaction.response.send_message(
                "Este desafio é exclusivo para a pessoa convidada.", ephemeral=True
            )
            return
        if self.aposta and get_volts(self.desafiante.id) < self.aposta:
            await interaction.response.edit_message(
                content="❌ Desafio cancelado: o desafiante não possui saldo suficiente.",
                embed=None, view=None
            )
            self.stop()
            return
        if self.aposta and get_volts(self.adversario.id) < self.aposta:
            await interaction.response.edit_message(
                content="❌ Desafio cancelado: você não possui Volts suficientes.",
                embed=None, view=None
            )
            self.stop()
            return

        if self.aposta:
            add_volts(self.desafiante.id, -self.aposta)
            add_volts(self.adversario.id, -self.aposta)

        jogo = BlackjackPartida(self.desafiante, self.adversario, self.aposta, self.desafiante)
        jogo.message = interaction.message
        if jogo.encerrado:
            jogo.preparar_encerramento()
        await interaction.response.edit_message(content=None, embed=jogo.criar_embed(), view=jogo)
        self.stop()

    @discord.ui.button(label="Recusar", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.adversario.id:
            await interaction.response.send_message(
                "Somente a pessoa convidada pode recusar este desafio.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content=f"❌ Desafio recusado por {interaction.user.display_name}.", embed=None, view=None
        )
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ O prazo para aceitar o desafio terminou.", view=self)
            except discord.HTTPException:
                pass


class BlackjackPartida(discord.ui.View):
    def __init__(self, jogador1, jogador2, aposta, primeiro):
        super().__init__(timeout=300)
        self.numero_partida = bj_proxima_partida()
        self.jogadores = [jogador1] if jogador2 is None else [jogador1, jogador2]
        self.aposta = aposta
        self.maos = {jogador1.id: [bj_comprar(), bj_comprar()]}
        if jogador2 is not None:
            self.maos[jogador2.id] = [bj_comprar(), bj_comprar()]
        self.dealer = [bj_comprar(), bj_comprar()] if jogador2 is None else []
        self.vez = primeiro.id
        self.parados = set()
        self.encerrado = False
        self.resultado = None
        self.resultado_tipo = None  # vitoria, derrota ou empate para o desafiante
        self.message = None
        self.mostrando_dealer = False

        if jogador2 is None:
            if bj_total(self.maos[jogador1.id]) == 21:
                self.finalizar_bot()
                self.preparar_encerramento()
        else:
            if bj_total(self.maos[jogador1.id]) == 21:
                self.parados.add(jogador1.id)
                self.vez = jogador2.id
            if bj_total(self.maos[jogador2.id]) == 21:
                self.parados.add(jogador2.id)
            if len(self.parados) == 2:
                self.finalizar_pvp()
                self.preparar_encerramento()

    def criar_embed(self):
        if not self.encerrado:
            cor = COR_PRINCIPAL
            descricao = "Partida em andamento. Consulte sua pontuação e aguarde sua vez."
        else:
            cor = {
                "vitoria": discord.Color.green(),
                "derrota": discord.Color.red(),
                "empate": discord.Color.gold(),
            }.get(self.resultado_tipo, COR_PRINCIPAL)
            descricao = "Partida encerrada. Confira o resultado abaixo."

        embed = discord.Embed(
            title="BLACK JACK • 21",
            description=descricao,
            color=cor
        )

        for indice, jogador in enumerate(self.jogadores):
            nome = "👤 Você" if indice == 0 else f"👤 Oponente — {discord.utils.escape_markdown(jogador.display_name)}"
            total = bj_total(self.maos[jogador.id])
            estado = " — ESTOUROU" if total > 21 else (
                " — PAROU" if jogador.id in self.parados and not self.encerrado else ""
            )
            valor_mao = bj_mostrar_mao(self.maos[jogador.id])
            embed.add_field(
                name=f"{nome}{estado}",
                value=valor_mao,
                inline=False
            )

        if len(self.jogadores) == 1:
            if self.encerrado or self.mostrando_dealer:
                dealer_texto = bj_mostrar_mao(self.dealer)
            else:
                dealer_texto = f"{bj_nome_carta(self.dealer[0])} · Carta oculta"
            embed.add_field(name="⚡ Ratinho", value=dealer_texto, inline=False)
        elif not self.encerrado:
            atual = next((j for j in self.jogadores if j.id == self.vez), None)
            nome_atual = "Você" if atual and atual.id == self.jogadores[0].id else "Oponente"
            embed.add_field(name="⏳ Vez de jogar", value=nome_atual, inline=False)

        valor_aposta = (
            f"{fmt_volts(self.aposta).replace(chr(42), '')} para cada participante"
            if self.aposta else
            "Partida amistosa — sem movimentação de Volts"
        )
        embed.add_field(
            name="💰 Valor da aposta",
            value=valor_aposta,
            inline=False
        )
        if self.encerrado and self.resultado:
            embed.add_field(
                name="🏁 Resultado final",
                value=self.resultado,
                inline=False
            )

        embed.set_footer(text=f"Partida de Blackjack n° {self.numero_partida}")
        return embed

    def preparar_encerramento(self):
        if any(getattr(item, "custom_id", None) == "bj_tentar_novamente" for item in self.children):
            return
        self.encerrado = True
        for item in list(self.children):
            self.remove_item(item)
        botao = discord.ui.Button(
            label="Tentar de novo",
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            custom_id="bj_tentar_novamente"
        )
        botao.callback = self.tentar_novamente
        self.add_item(botao)

    async def tentar_novamente(self, interaction: discord.Interaction):
        if interaction.user.id not in [j.id for j in self.jogadores]:
            await interaction.response.send_message(
                "Somente os participantes desta partida podem jogar novamente.", ephemeral=True
            )
            return
        if self.aposta and get_volts(interaction.user.id) < self.aposta:
            await interaction.response.send_message(
                f"❌ Você não possui saldo suficiente para repetir a aposta de {fmt_volts(self.aposta)}.",
                ephemeral=True
            )
            return

        if len(self.jogadores) == 1:
            jogador = self.jogadores[0]
            novo = BlackjackPartida(jogador, None, self.aposta, jogador)
            novo.message = interaction.message
            if novo.encerrado:
                novo.preparar_encerramento()
            # Substitui a partida encerrada na mesma mensagem, sem aviso adicional.
            await interaction.response.edit_message(embed=novo.criar_embed(), view=novo)
            return

        desafiante = interaction.user
        adversario = next(j for j in self.jogadores if j.id != interaction.user.id)
        if self.aposta and get_volts(adversario.id) < self.aposta:
            await interaction.response.send_message(
                f"❌ {adversario.display_name} não possui Volts suficientes para cobrir novamente esta aposta.",
                ephemeral=True
            )
            return
        desafio = BlackjackDesafio(desafiante, adversario, self.aposta)
        desafio.message = interaction.message
        texto = (
            f"**NOVO DESAFIO DE BLACKJACK**\n{adversario.mention}, "
            f"{desafiante.display_name} quer repetir a partida."
        )
        texto += f"\n**Aposta:** {fmt_volts(self.aposta)} para cada participante." if self.aposta else "\n**Modalidade:** amistosa, sem aposta."
        await interaction.response.edit_message(content=texto, embed=None, view=desafio)

    def finalizar_bot(self):
        self.encerrado = True
        jogador = self.jogadores[0]
        pontos = bj_total(self.maos[jogador.id])
        pontos_dealer = bj_total(self.dealer)
        if pontos > 21:
            self.resultado = "Você ultrapassou 21 pontos. O Ratinho venceu."
            self.resultado_tipo = "derrota"
            if self.aposta:
                add_volts(jogador.id, -self.aposta)
        elif pontos_dealer > 21 or pontos > pontos_dealer:
            self.resultado = "Você venceu a partida!"
            self.resultado_tipo = "vitoria"
            if self.aposta:
                add_volts(jogador.id, self.aposta)
        elif pontos == pontos_dealer:
            self.resultado = "Empate. Seu saldo não foi alterado."
            self.resultado_tipo = "empate"
        else:
            self.resultado = "O Ratinho venceu a partida."
            self.resultado_tipo = "derrota"
            if self.aposta:
                add_volts(jogador.id, -self.aposta)

    async def atualizar_mensagem(self):
        if self.message:
            try:
                await self.message.edit(embed=self.criar_embed(), view=self)
            except discord.HTTPException:
                pass

    async def finalizar_bot_animado(self):
        # Revela as duas cartas iniciais e compra cada carta adicional separadamente.
        self.mostrando_dealer = True
        # Pequena pausa antes de revelar a segunda carta do Ratinho.
        await asyncio.sleep(1)
        await self.atualizar_mensagem()
        while bj_total(self.dealer) < 17:
            await asyncio.sleep(1)
            self.dealer.append(bj_comprar())
            await self.atualizar_mensagem()
        self.finalizar_bot()
        self.preparar_encerramento()
        await self.atualizar_mensagem()

    def finalizar_pvp(self):
        self.encerrado = True
        a, b = self.jogadores
        pa, pb = bj_total(self.maos[a.id]), bj_total(self.maos[b.id])
        if pa > 21:
            vencedor = b
        elif pb > 21:
            vencedor = a
        elif pa > pb:
            vencedor = a
        elif pb > pa:
            vencedor = b
        else:
            vencedor = None
        if vencedor:
            if vencedor.id == a.id:
                self.resultado_tipo = "vitoria"
                self.resultado = "Você venceu e recebeu o total da aposta!"
            else:
                self.resultado_tipo = "derrota"
                self.resultado = f"{discord.utils.escape_markdown(vencedor.display_name)} venceu e recebeu o total da aposta."
            if self.aposta:
                add_volts(vencedor.id, self.aposta * 2)
        else:
            self.resultado_tipo = "empate"
            self.resultado = "Empate. As apostas foram devolvidas aos participantes."
            if self.aposta:
                add_volts(a.id, self.aposta)
                add_volts(b.id, self.aposta)

    @discord.ui.button(label="Pedir carta", emoji="🃏", style=discord.ButtonStyle.secondary)
    async def pedir(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.encerrado or interaction.user.id != self.vez:
            await interaction.response.send_message("Não é sua vez de jogar.", ephemeral=True)
            return
        mao = self.maos[self.vez]
        mao.append(bj_comprar())
        total = bj_total(mao)

        if len(self.jogadores) == 1:
            if total > 21:
                self.finalizar_bot()
                self.preparar_encerramento()
                await interaction.response.edit_message(embed=self.criar_embed(), view=self)
                return
            if total == 21:
                await interaction.response.defer()
                await self.finalizar_bot_animado()
                return
        else:
            if total > 21:
                self.parados.add(self.vez)
                self.finalizar_pvp()
                self.preparar_encerramento()
                await interaction.response.edit_message(embed=self.criar_embed(), view=self)
                return
            if total == 21:
                self.parados.add(self.vez)
                self.proxima_vez()
        await self.responder_jogada(interaction)

    @discord.ui.button(label="Parar", emoji="✋", style=discord.ButtonStyle.secondary)
    async def parar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.encerrado or interaction.user.id != self.vez:
            await interaction.response.send_message("Não é sua vez de jogar.", ephemeral=True)
            return
        if len(self.jogadores) == 1:
            await interaction.response.defer()
            await self.finalizar_bot_animado()
            return
        self.parados.add(self.vez)
        self.proxima_vez()
        await self.responder_jogada(interaction)

    def proxima_vez(self):
        for jogador in self.jogadores:
            if jogador.id not in self.parados:
                self.vez = jogador.id
                return
        self.finalizar_pvp()
        self.preparar_encerramento()

    async def responder_jogada(self, interaction):
        if self.encerrado:
            self.preparar_encerramento()
        await interaction.response.edit_message(embed=self.criar_embed(), view=self)

    async def on_timeout(self):
        if self.encerrado:
            return
        self.encerrado = True
        if self.aposta and len(self.jogadores) == 2:
            for jogador in self.jogadores:
                add_volts(jogador.id, self.aposta)
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    content="⌛ Partida encerrada por inatividade. As apostas foram devolvidas, quando aplicável.",
                    embed=self.criar_embed(), view=self
                )
            except discord.HTTPException:
                pass


@bot.hybrid_command(
    name="bj",
    description="Joga Blackjack apostando Volts ou por diversão"
)
@app_commands.describe(
    valor="Quantidade de Volts, 'all' para apostar todo o saldo (opcional)",
    membro="Pessoa para desafiar (opcional; sem pessoa, joga contra o Ratinho)"
)
async def blackjack(ctx, valor: str = None, membro: discord.Member = None):
    if valor and membro is None:
        achou = re.fullmatch(r"<@!?(\d+)>", valor)
        if achou:
            membro = ctx.guild.get_member(int(achou.group(1)))
            valor = None

    try:
        aposta_todos = bool(valor and valor.strip().lower() == "all")
        aposta = get_volts(ctx.author.id) if aposta_todos else bj_parse_valor(valor)
        if aposta_todos and aposta <= 0:
            await ctx.send("❌ Você não possui Volts disponíveis para apostar.")
            return
    except ValueError:
        await ctx.send("❌ Valor inválido. Exemplos: `vbj 200k`, `vbj all` ou `vbj 200k @pessoa`.")
        return

    if aposta < 0:
        await ctx.send("❌ A aposta não pode ser negativa.")
        return
    if aposta and get_volts(ctx.author.id) < aposta:
        await ctx.send(f"❌ Você precisa ter pelo menos {fmt_volts(aposta)} para apostar.")
        return
    if membro and membro.id == ctx.author.id:
        await ctx.send("❌ Você não pode jogar Blackjack contra si mesmo.")
        return
    if membro and membro.bot:
        await ctx.send("❌ Você só pode desafiar pessoas, não outros bots.")
        return

    if membro:
        if aposta and get_volts(membro.id) < aposta:
            await ctx.send(f"❌ {membro.mention} não tem Volts suficientes para cobrir esta aposta.")
            return
        desafio = BlackjackDesafio(ctx.author, membro, aposta)
        mensagem = f"**DESAFIO DE BLACKJACK**\n{membro.mention}, {ctx.author.mention} convidou você para uma partida."
        mensagem += f"\n**Aposta:** {fmt_volts(aposta)} para cada participante." if aposta else "\n**Modalidade:** amistosa, sem movimentação de Volts."
        mensagem += "\nA partida começará após a aceitação. Prazo: 60 segundos."
        desafio.message = await ctx.send(mensagem, view=desafio)
    else:
        jogo = BlackjackPartida(ctx.author, None, aposta, ctx.author)
        jogo.message = await ctx.send(embed=jogo.criar_embed(), view=jogo)


# ============================================================
#  6. COMANDOS
# ============================================================
@bot.hybrid_command(
    name="rank",
    description="Mostra o ranking global e local de Volts"
)
@commands.guild_only()
async def rank(ctx):
    embed = discord.Embed(
        title="⚡ Ranking de Volts",
        description=(
            "Escolha qual classificação deseja consultar usando os botões abaixo.\n\n"
            "🌎 **Global:** os usuários com mais Volts no banco global do Ratinho.\n"
            "🏠 **Local:** os usuários com mais Volts neste servidor."
        ),
        color=COR_PRINCIPAL,
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}")
    view = PainelRankVolts(ctx.guild, ctx.author)
    await ctx.send(embed=embed, view=view)


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
    dados_economia = carregar()
    if not ja_resgatou_daily(membro.id, dados_economia):
        embed = discord.Embed(
            title="⚠️  Daily necessário",
            description=(
                f"{membro.mention} precisa resgatar o **Daily de Volts** "
                "pelo menos uma vez antes de receber transferências."
            ),
            color=COR_ERRO
        )
        await ctx.send(embed=embed)
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
    fuso_brasilia = timezone(timedelta(hours=-3))
    hoje = datetime.now(fuso_brasilia).date()
    if uid not in dados:
        dados[uid] = {"volts": 0, "last_daily": 0}
    ultimo_resgate = dados[uid].get("last_daily", 0)
    data_ultimo = dados[uid].get("last_daily_date")
    if not data_ultimo and ultimo_resgate:
        data_ultimo = datetime.fromtimestamp(ultimo_resgate, fuso_brasilia).date().isoformat()
    if data_ultimo == hoje.isoformat():
        amanha = datetime.combine(hoje + timedelta(days=1), datetime.min.time(), tzinfo=fuso_brasilia)
        falta = max(0, int((amanha - datetime.now(fuso_brasilia)).total_seconds()))
        horas = falta // 3600
        minutos = (falta % 3600) // 60
        embed = discord.Embed(
            title="⏰  Recompensa diária indisponível",
            description="Você já resgatou sua recompensa diária. Volte depois da meia-noite!",
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
    dados[uid]["last_daily_date"] = hoje.isoformat()
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
        value="Disponível novamente à meia-noite (horário de Brasília).",
        inline=False
    )
    embed.set_footer(
        text=f"Solicitado por {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.send(embed=embed)


@bot.hybrid_command(
    name="roubar",
    description="Tenta roubar 20% dos volts de outro membro"
)
async def roubar(ctx, membro: discord.Member = None):
    """Permite até 3 tentativas em 24 horas; cada vítima só pode ser roubada uma vez por dia."""
    if membro is None:
        embed = discord.Embed(
            title="⚠️  Comando incompleto",
            description="Informe quem você deseja tentar roubar.\n\n**Uso:** `v roubar @usuário` ou `/roubar usuário`",
            color=COR_ERRO
        )
        await ctx.send(embed=embed)
        return

    if membro.bot:
        await ctx.send(embed=discord.Embed(
            title="⚠️  Alvo inválido",
            description="Não é possível roubar contas de bots.",
            color=COR_ERRO
        ))
        return
    if membro.id == ctx.author.id:
        await ctx.send(embed=discord.Embed(
            title="⚠️  Operação inválida",
            description="Você não pode tentar roubar a si mesmo.",
            color=COR_ERRO
        ))
        return

    dados = carregar()
    uid = str(ctx.author.id)
    alvo_id = str(membro.id)
    agora = time.time()
    fuso_brasilia = timezone(timedelta(hours=-3))
    hoje = datetime.now(fuso_brasilia).date().isoformat()

    dados.setdefault(uid, {"volts": 0, "last_daily": 0})
    dados.setdefault(alvo_id, {"volts": 0, "last_daily": 0})
    dados[uid].setdefault("volts", 0)
    dados[alvo_id].setdefault("volts", 0)

    if not ja_resgatou_daily(membro.id, dados):
        embed = discord.Embed(
            title="⚠️  Daily necessário",
            description=(
                f"{membro.mention} precisa resgatar o **Daily de Volts** "
                "pelo menos uma vez antes de poder ser alvo de um roubo."
            ),
            color=COR_ERRO
        )
        await ctx.send(embed=embed)
        return

    # Limite móvel: no máximo três tentativas dentro das últimas 24 horas.
    usos = dados[uid].get("roubar_usos", [])
    if not isinstance(usos, list):
        usos = []
    usos = [float(t) for t in usos if isinstance(t, (int, float)) and agora - float(t) < 86400]
    if len(usos) >= 3:
        restante = max(0, int(86400 - (agora - min(usos))))
        horas, resto = divmod(restante, 3600)
        minutos = resto // 60
        embed = discord.Embed(
            title="⏳  Limite de tentativas atingido",
            description="Você já utilizou suas **3 tentativas** de roubo nas últimas 24 horas.",
            color=COR_ERRO
        )
        embed.add_field(name="Próxima tentativa", value=f"Disponível em **{horas}h {minutos}min**.", inline=False)
        embed.set_footer(text="O limite é renovado conforme cada tentativa completa 24 horas.")
        await ctx.send(embed=embed)
        return

    data_ultimo_roubo = dados[alvo_id].get("roubado_em_data")
    if data_ultimo_roubo == hoje:
        embed = discord.Embed(
            title="🛡️  Alvo protegido",
            description=f"{membro.mention} já foi roubado hoje e não pode ser roubado novamente até a próxima virada do dia.",
            color=COR_ERRO
        )
        embed.add_field(name="Proteção", value="A vítima só pode sofrer um roubo bem-sucedido por dia.", inline=False)
        await ctx.send(embed=embed)
        return

    # Toda tentativa válida consome uma das três utilizações, inclusive em caso de falha.
    usos.append(agora)
    dados[uid]["roubar_usos"] = usos
    saldo_alvo = max(0, int(dados[alvo_id]["volts"]))

    if saldo_alvo <= 0:
        salvar(dados)
        embed = discord.Embed(
            title="🏦  Carteira vazia",
            description=f"{membro.mention} não possui Volts para serem roubados.",
            color=COR_ERRO
        )
        embed.add_field(name="Tentativas restantes", value=f"**{3 - len(usos)}/3** nas próximas 24 horas", inline=False)
        await ctx.send(embed=embed)
        return

    if random.random() < 0.70:
        valor = int(saldo_alvo * 0.20)
        if valor < 1:
            salvar(dados)
            embed = discord.Embed(
                title="⚠️  Saldo insuficiente para o roubo",
                description=f"O saldo de {membro.mention} é muito baixo para transferir 20% (mínimo de 1 Volt).",
                color=COR_ERRO
            )
            await ctx.send(embed=embed)
            return
        dados[alvo_id]["volts"] -= valor
        dados[uid]["volts"] = int(dados[uid].get("volts", 0)) + valor
        dados[alvo_id]["roubado_em_data"] = hoje
        salvar(dados)

        embed = discord.Embed(
            title="💰  Roubo bem-sucedido!",
            description=f"{ctx.author.mention} conseguiu roubar **20% dos Volts** de {membro.mention}!",
            color=COR_SUCESSO,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🦹 Ladrão", value=ctx.author.mention, inline=True)
        embed.add_field(name="🎯 Vítima", value=membro.mention, inline=True)
        embed.add_field(name="⚡ Volts roubados", value=fmt_volts(valor), inline=False)
        embed.add_field(name="Seu novo saldo", value=fmt_volts(dados[uid]["volts"]), inline=True)
        embed.add_field(name="Saldo da vítima", value=fmt_volts(dados[alvo_id]["volts"]), inline=True)
        embed.add_field(name="Tentativas restantes", value=f"**{3 - len(usos)}/3** nas próximas 24 horas", inline=False)
        embed.set_footer(text="A vítima estará protegida contra novos roubos até amanhã (horário de Brasília).")
    else:
        salvar(dados)
        embed = discord.Embed(
            title="🚨  Roubo frustrado!",
            description=f"{ctx.author.mention}, sua tentativa de roubar {membro.mention} falhou! A vítima conseguiu escapar.",
            color=COR_ERRO,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Chance de sucesso", value="70%", inline=True)
        embed.add_field(name="Chance de falha", value="30%", inline=True)
        embed.add_field(name="Tentativas restantes", value=f"**{3 - len(usos)}/3** nas próximas 24 horas", inline=False)
        embed.set_footer(text="Uma tentativa foi contabilizada. Tente novamente quando seu limite renovar.")

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

@bot.hybrid_command(name="clear", description="Apaga até 1.000 mensagens do canal")
@app_commands.default_permissions(manage_messages=True)
@commands.has_permissions(manage_messages=True)
async def clear(ctx, quantidade: app_commands.Range[int, 1, 1000] = 100):
    if ctx.guild is None:
        return

    try:
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)

        # No comando por prefixo, inclui a própria mensagem do comando
        # na busca para removê-la junto, sem contar como mensagem apagada.
        limite_busca = quantidade if ctx.interaction else quantidade + 1
        apagadas = await ctx.channel.purge(
            limit=limite_busca,
            check=lambda mensagem: not mensagem.pinned
        )

        total_apagado = sum(
            1 for mensagem in apagadas
            if ctx.interaction or mensagem.id != ctx.message.id
        )

        resposta = f"🧹 Foram apagadas **{total_apagado}** mensagem(ns)."
        if ctx.interaction:
            await ctx.followup.send(resposta, ephemeral=True)
        else:
            await ctx.send(resposta, delete_after=8)

    except discord.Forbidden:
        mensagem_erro = "❌ Não tenho permissão para apagar mensagens. Verifique se possuo **Gerenciar mensagens**."
        if ctx.interaction:
            await ctx.followup.send(mensagem_erro, ephemeral=True)
        else:
            await ctx.send(mensagem_erro, delete_after=10)
    except discord.HTTPException as erro:
        print(f"Erro no comando clear: {erro}")
        mensagem_erro = "❌ Não foi possível apagar as mensagens. Verifique minhas permissões e tente novamente."
        if ctx.interaction:
            await ctx.followup.send(mensagem_erro, ephemeral=True)
        else:
            await ctx.send(mensagem_erro, delete_after=10)

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        mensagem = "❌ Você precisa da permissão **Gerenciar mensagens** para usar este comando."
    elif isinstance(error, commands.BotMissingPermissions):
        mensagem = "❌ O Ratinho precisa da permissão **Gerenciar mensagens** neste canal."
    else:
        print(f"Erro ao executar clear: {error}")
        mensagem = "❌ Ocorreu um erro ao executar o comando clear. Verifique as permissões e tente novamente."

    try:
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(mensagem, ephemeral=True)
            else:
                await ctx.followup.send(mensagem, ephemeral=True)
        else:
            await ctx.send(mensagem, delete_after=10)
    except discord.HTTPException as erro:
        print(f"Não foi possível enviar o erro do clear: {erro}")

@bot.hybrid_command(
    name="painel-cargos",
    description="Abre a configuração do painel de cargos (só ADM)"
)
@app_commands.default_permissions(administrator=True)
@commands.has_permissions(administrator=True)
async def painel_cargos(ctx):
    if ctx.guild is None:
        await ctx.send("❌ Use esse comando dentro de um servidor!", ephemeral=True)
        return
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Você precisa ser administrador!", ephemeral=True)
        return
    await ctx.send(embed=embed_config_painel_cargos(ctx.guild.id), view=PainelCargosConfigView(ctx.guild.id))

@painel_cargos.error
async def painel_cargos_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você precisa ser administrador para configurar o painel de cargos!", ephemeral=True)
    else:
        print(f"Erro no comando painel-cargos: {error}")
        try:
            await ctx.send("❌ Ocorreu um erro ao abrir a configuração do painel de cargos.", ephemeral=True)
        except Exception:
            pass


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
    description="Cria uma mensagem com embed personalizada (só ADM)"
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.rename(mensagem_embed="mensagem-embed")
@app_commands.describe(
    mensagem="Texto que aparece acima e fora da embed (opcional)",
    mensagem_embed="Texto que aparece dentro da embed (opcional)",
    cor="Cor: nome ou #hex. Se vazio, fica amarelo",
    midia="Link de imagem (opcional)"
)
async def criar_embed(
    interaction: discord.Interaction,
    mensagem: str = None,
    mensagem_embed: str = None,
    cor: str = None,
    midia: str = None
):
    mensagem = (mensagem or "").strip()
    mensagem_embed = (mensagem_embed or "").strip()
    midia = (midia or "").strip()

    if not mensagem and not mensagem_embed and not midia:
        await interaction.response.send_message(
            "⚠️ Adicione pelo menos um conteúdo: uma **mensagem**, "
            "uma **mensagem-embed** ou uma **imagem**.",
            ephemeral=True
        )
        return

    if midia and not midia.lower().startswith(("https://", "http://")):
        await interaction.response.send_message(
            "❌ O link da imagem precisa começar com http:// ou https://.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(color=parse_cor(cor))

    if mensagem_embed:
        embed.description = mensagem_embed
    if midia:
        embed.set_image(url=midia)

    await interaction.channel.send(
        content=mensagem or None,
        embed=embed if mensagem_embed or midia else None
    )
    await interaction.followup.send(
        "✅ Mensagem enviada!",
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
                "`v atm` • `v daily` • `vrank` • "
                "`v volts pagar @usuário 100` • "
                "`v configurar`"
            ),
            inline=False
        )
        await message.channel.send(embed=embed)
    await bot.process_commands(message)

keep_alive()
bot.run(os.getenv("TOKEN"))    
