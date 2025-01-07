import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timezone
import sqlite3
import re

# TOKEN
bot_token = "TOKEN!"  # Replace with your actual bot token

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Folder and Database Path
FOLDER_PATH = "Wrox DB"
DB_PATH = os.path.join(FOLDER_PATH, "bot_config.db")

# Database Initialization
def init_db():
    if not os.path.exists(FOLDER_PATH):
        print("📁 [WARNING] Folder not found. Creating folder...")
        os.makedirs(FOLDER_PATH)

    if not os.path.exists(DB_PATH):
        print("📄 [INFO] Database file not found. Creating a new database...")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                banner_url TEXT,
                icon_url TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS colors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                hex_color TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ [INFO] Database created successfully.")
    else:
        print("✅ [INFO] Database found. Loading configurations...")


def insert_default_colors():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    default_colors = [
        ("Red", "#FF0000"), ("Blue", "#0000FF"), ("Green", "#00FF00"),
        ("Yellow", "#FFFF00"), ("Orange", "#FFA500"), ("Purple", "#800080"),
        ("Pink", "#FFC0CB"), ("White", "#FFFFFF"), ("Black", "#000000"),
        ("Gray", "#808080"), ("Brown", "#A52A2A"), ("Teal", "#008080"),
        ("Maroon", "#800000"), ("Gold", "#FFD700"),
    ]

    for color_name, hex_color in default_colors:
        c.execute('INSERT OR IGNORE INTO colors (name, hex_color) VALUES (?, ?)', (color_name, hex_color))

    conn.commit()
    conn.close()

# Custom Bot Class
class AdvancedBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)
        self.start_time = datetime.now()
        self.banner_url = None
        self.icon_url = None
        self.color_map = {}
        self.load_config()

    async def setup_hook(self):
        await self.tree.sync()

    def load_config(self):
        if not os.path.exists(DB_PATH):
            print("❌ Database not found, please ensure the bot is correctly initialized!")
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("SELECT banner_url, icon_url FROM settings WHERE id = 1")
        data = c.fetchone()
        if data:
            self.banner_url, self.icon_url = data

        c.execute("SELECT name, hex_color FROM colors")
        self.color_map = {name.lower(): hex_color for name, hex_color in c.fetchall()}

        conn.close()

# Instantiate the bot
bot = AdvancedBot()

# Initialize Database and Default Colors
init_db()
insert_default_colors()

# Helper Functions
def hex_to_color(hex_code):
    try:
        rgb = tuple(int(hex_code.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        return discord.Color.from_rgb(*rgb)
    except ValueError:
        return None

def is_valid_hex(hex_color):
    return bool(re.match(r'^#[0-9A-Fa-f]{6}$', hex_color))

# Event: Bot Ready
@bot.event
async def on_ready():
    print(f"✅ Bot started as {bot.user}")
    print(f"📂 Database and configurations loaded successfully.")

@bot.tree.command(name="ann", description="📢 Create an announcement.")
@app_commands.describe(title="📋 Title of the announcement.", description="📝 Description of the announcement.", color_name="🎨 Optional color name or hex code.")
async def ann(interaction: discord.Interaction, title: str = None, description: str = None, color_name: str = None):
    if not title or not description:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Usage Error",
                description="You must provide a title and description.\n\n**Usage:** `/ann <title> <description> [color]`",
                color=discord.Color.red()
            ), ephemeral=True
        )
        return

    color = hex_to_color(color_name) if color_name and color_name.startswith("#") else hex_to_color(bot.color_map.get(color_name.lower()))
    if not color:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Invalid Color",
                description="Invalid color format or name. Use `/colorshelp` to see available colors.",
                color=discord.Color.red()
            ), ephemeral=True
        )
        return

    embed = discord.Embed(title=title, description=description, color=color)
    if bot.banner_url:
        embed.set_image(url=bot.banner_url)
    if bot.icon_url:
        embed.set_thumbnail(url=bot.icon_url)
    embed.set_footer(text=f"Announced by {interaction.user}", icon_url=interaction.user.avatar.url)

    # Send only to the interaction channel
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addcolor", description="🎨 Add a new custom color.")
@app_commands.describe(name="📋 Name of the color.", hexcolor="🛠️ Hexadecimal color code.")
async def addcolor(interaction: discord.Interaction, name: str = None, hexcolor: str = None):
    if not name or not hexcolor:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Usage Error",
                description="Provide a color name and hex code.\n\n**Usage:** `/addcolor <name> <hexcolor>`",
                color=discord.Color.red()
            ), ephemeral=True)
        return

    if name.lower() in bot.color_map:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Color Exists",
                description=f"The color name `{name}` is already in use.",
                color=discord.Color.red()
            ), ephemeral=True)
        return

    if not is_valid_hex(hexcolor):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Invalid Hex Code",
                description="Provide a valid hex code (e.g., `#FF5733`).",
                color=discord.Color.red()
            ), ephemeral=True)
        return

    bot.color_map[name.lower()] = hexcolor
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO colors (name, hex_color) VALUES (?, ?)", (name, hexcolor))
    conn.commit()
    conn.close()

    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ Color Added",
            description=f"Color `{name}` with code `{hexcolor}` added successfully.",
            color=discord.Color.green()
        ), ephemeral=True)

@bot.tree.command(name="colorshelp", description="🛠️ View all available colors.")
async def colorshelp(interaction: discord.Interaction):
    embed = discord.Embed(title="🎨 Available Colors", color=discord.Color.blue())
    for name, hex_color in bot.color_map.items():
        embed.add_field(name=f"🖌️ {name.capitalize()}", value=hex_color, inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setbanner", description="🖼️ Set a banner for announcements.")
@app_commands.describe(url="📷 URL of the banner image.")
async def setbanner(interaction: discord.Interaction, url: str):
    bot.banner_url = url
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (id, banner_url) VALUES (1, ?)", (url,))
    conn.commit()
    conn.close()

    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ Banner Set",
            description=f"The banner for announcements is set to:\n{url}",
            color=discord.Color.green(),
        ), ephemeral=True
    )

@bot.tree.command(name="seticon", description="🔗 Set an icon for announcements.")
@app_commands.describe(type="🛠️ Use 'bot' for bot's avatar or 'custom' for a URL.", value="Custom icon URL for 'custom' type.")
async def seticon(interaction: discord.Interaction, type: str, value: str = None):
    if type.lower() == "bot":
        bot.icon_url = bot.user.avatar.url
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (id, icon_url) VALUES (1, ?)", (bot.icon_url,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Icon Set",
                description="Icon set to the bot's current avatar.",
                color=discord.Color.green(),
            ), ephemeral=True
        )
    elif type.lower() == "custom" and value:
        bot.icon_url = value
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (id, icon_url) VALUES (1, ?)", (value,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Custom Icon Set",
                description=f"Custom icon URL set to:\n{value}",
                color=discord.Color.green(),
            ), ephemeral=True
        )
    else:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Invalid Input",
                description="Use `type` as 'bot' or 'custom' with a valid value.\n\n**Usage:** `/seticon <type> [value]`",
                color=discord.Color.red(),
            ), ephemeral=True
        )

@bot.tree.command(name="help", description="ℹ️ Show the list of commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="ℹ️ Help",
        description="List of commands with descriptions:",
        color=discord.Color.gold(),
    )
    embed.add_field(name="/help", value="ℹ️ Show this help message.", inline=False)
    embed.add_field(name="/ann", value="📢 Create an announcement.\n**Usage:** `/ann <title> <description> [color]`", inline=False)
    embed.add_field(name="/addcolor", value="🎨 Add a new color.\n**Usage:** `/addcolor <name> <hexcolor>`", inline=False)
    embed.add_field(name="/colorshelp", value="🛠️ View all available colors.", inline=False)
    embed.add_field(name="/setbanner", value="🖼️ Set a banner image for announcements.\n**Usage:** `/setbanner <url>`", inline=False)
    embed.add_field(name="/seticon", value="🔗 Set an icon for announcements.\n**Usage:** `/seticon <type> [value]`", inline=False)
    embed.add_field(name="/botinfo", value="🤖 Get bot's info.", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="botinfo", description="🤖 Display detailed information about the bot with live updates.")
async def botinfo(interaction: discord.Interaction):
    def calculate_times():
        current_time = datetime.now(timezone.utc)  # Ensure timezone-aware datetime
        bot_uptime = current_time - bot.start_time.replace(tzinfo=timezone.utc)  # Ensure bot.start_time is timezone-aware
        joined_elapsed = current_time - interaction.guild.me.joined_at.replace(tzinfo=timezone.utc)  # Ensure joined_at is timezone-aware

        uptime_str = (
            f"{bot_uptime.days} days, {bot_uptime.seconds // 3600} hours, "
            f"{(bot_uptime.seconds % 3600) // 60} minutes, {bot_uptime.seconds % 60} seconds"
        )
        joined_elapsed_str = (
            f"{joined_elapsed.days} days, {joined_elapsed.seconds // 3600} hours, "
            f"{(joined_elapsed.seconds % 3600) // 60} minutes, {joined_elapsed.seconds % 60} seconds"
        )

        return uptime_str, joined_elapsed_str

    # Function to create the embed
    def create_embed():
        uptime_str, joined_elapsed_str = calculate_times()

        embed = discord.Embed(
            title="🤖 Bot Information (Live Updates)",
            description="This embed dynamically updates every second with the latest bot statistics.",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=bot.user.avatar.url)

        # Bot Details
        embed.add_field(name="**Bot Name**", value=f"`{bot.user.name}`", inline=True)
        embed.add_field(name="**Bot Version**", value="`1.2`", inline=True)
        embed.add_field(name="**Developer**", value="`Wrox/Zpyrx`", inline=True)

        # Performance
        latency = round(bot.latency * 1000)  # Convert to milliseconds
        embed.add_field(name="**Ping**", value=f"`{latency} ms`", inline=True)

        # Server Details
        embed.add_field(
            name="**Joined Server**",
            value=f"Elapsed: `{joined_elapsed_str}`\nDate: `{interaction.guild.me.joined_at.strftime('%d %B %Y')}`",
            inline=False
        )

        # Uptime
        embed.add_field(
            name="**Bot Uptime**",
            value=f"Uptime: `{uptime_str}`\nDate Started: `{bot.start_time.strftime('%d %B %Y')}`",
            inline=False
        )

        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.avatar.url)
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    try:
        initial_embed = create_embed()
        await interaction.response.send_message(embed=initial_embed)
        live_message = await interaction.original_response()

        # Dynamic embed updates for 15 seconds (one update every second)
        for _ in range(15):
            await asyncio.sleep(1)  # Wait for 1 second
            updated_embed = create_embed()
            await live_message.edit(embed=updated_embed)

        # Notify the user that live updates have ended
        final_embed = discord.Embed(
            title="⏳ Live Updates Ended",
            description="The live updates for this embed have stopped. Thank you for using `/botinfo`.",
            color=discord.Color.orange()
        )
        final_embed.set_footer(text="Live Updates Expired", icon_url=bot.user.avatar.url)
        final_embed.timestamp = datetime.now(timezone.utc)
        await live_message.edit(embed=final_embed)

    except Exception as e:
        print(f"Error during /botinfo execution: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred while running the `/botinfo` command.", ephemeral=True)

bot.run(bot_token)  # Start the bot
