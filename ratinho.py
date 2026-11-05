import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="v", intents=intents)

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    # Só o status da lua, sem atividade
    await bot.change_presence(status=discord.Status.idle)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        await message.channel.send(f"Olá {message.author.mention}! Eu sou o Ratinho e meu prefixo é v")

    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
