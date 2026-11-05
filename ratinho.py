from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import os

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

# Parte do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="v", intents=intents)

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    await bot.change_presence(status=discord.Status.idle)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user.mentioned_in(message):
        await message.channel.send(f"Olá {message.author.mention}! Eu sou o Ratinho e meu prefixo é v")
    await bot.process_commands(message)

keep_alive()
bot.run(os.getenv("TOKEN"))
