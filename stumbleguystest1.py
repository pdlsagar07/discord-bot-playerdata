# made by sagar
# the x-key used as stumble_key is provided by stumblelabs

import discord
from discord import app_commands
import requests
from datetime import datetime
from typing import Optional, Dict
import os
from dotenv import load_dotenv


load_dotenv()


STUMBLE_KEY = os.getenv("STUMBLE_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

class StumbleLabsAPI:
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stumblelabs.net/api/live"
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        })
    
    def search_by_username(self, username: str) -> Optional[Dict]:
        """Search for a player by username"""
        username = username.strip('"\' ').replace('"', '').replace("'", "")
        
        try:
            response = self.session.post(
                f"{self.base_url}/users/search",
                json={"username": username}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('data')
            return None
            
        except Exception as e:
            print(f"API Error: {e}")
            return None

# Create bot instance
class StumbleBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = False
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.api = StumbleLabsAPI(STUMBLE_KEY)

bot = StumbleBot()

#COMMAND 1: /username -
@bot.tree.command(name="username", description="Get complete Stumble Guys player data")
@app_commands.describe(username="The Stumble Guys username to search for")
@app_commands.guild_only()
async def username_command(interaction: discord.Interaction, username: str):
    if interaction.guild is None:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    async with interaction.channel.typing():
        player = bot.api.search_by_username(username)
        
        if not player:
            embed = discord.Embed(
                title="❌ Player Not Found",
                description=f"No player found with username `{username}`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = await create_full_player_embed(player, f"Username: {username}")
        await interaction.followup.send(embed=embed)

#COMMAND 2: /usernamehistory - Shows ONLY username history 
@bot.tree.command(name="usernamehistory", description="view username history")
@app_commands.describe(username="The Stumble Guys username to check history for")
@app_commands.guild_only()
async def usernamehistory_command(interaction: discord.Interaction, username: str):
    if interaction.guild is None:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    async with interaction.channel.typing():
        player = bot.api.search_by_username(username)
        
        if not player:
            embed = discord.Embed(
                title="❌ Player Not Found",
                description=f"No player found with username `{username}`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = await create_history_embed(player)
        await interaction.followup.send(embed=embed)


async def create_full_player_embed(player: Dict, search_info: str = None) -> discord.Embed:
    """Create embed with player data"""
    
    embed = discord.Embed(
        title=f"🎮 {player.get('userName', 'Unknown')}",
        color=discord.Color.blue()
    )
    
    if search_info:
        embed.description = f"*{search_info}*"
    
    # stumbledata
    trophies = player.get('trophies', 0)
    crowns = player.get('crowns', 0)
    
    embed.add_field(name="🏆 Trophies", value=f"**{trophies:,}**", inline=True)
    embed.add_field(name="👑 Crowns", value=f"**{crowns:,}**", inline=True)
    embed.add_field(name="🌍 Country", value=f"**{player.get('country', 'Unknown')}**", inline=True)
    
    # Status
    status = "🟢 Online" if player.get('isOnline') else "🔴 Offline"
    embed.add_field(name="Status", value=status, inline=True)
    
    # Platform
    platform = player.get('nativePlatformName', 'Unknown').title()
    embed.add_field(name="📱 Platform", value=f"**{platform}**", inline=True)
    
    # Level
    if player.get('xpRoadInfo'):
        level = player['xpRoadInfo'].get('level', 0)
        embed.add_field(name="⭐ Level", value=f"**{level}**", inline=True)
    
    # Clan
    if player.get('clan'):
        clan = player['clan']
        embed.add_field(
            name="👥 Clan",
            value=f"**{clan.get('name', 'Unknown')}** [{clan.get('tag', '???')}]",
            inline=False
        )
    
    # username history (<5)
    if player.get('usernameHistory') and len(player['usernameHistory']) > 1:
        history = player.get('usernameHistory', [])
        recent_history = history[-5:] if len(history) > 5 else history
        current_name = player.get('userName', '')
        
        history_text = ""
        for name in recent_history:
            if name == current_name:
                history_text += f"• **{name}** (current)\n"
            else:
                history_text += f"• {name}\n"
        
        embed.add_field(
            name=f"📝 Recent Usernames (last {len(recent_history)} of {len(history)})", 
            value=history_text, 
            inline=False
        )
    
    # Skin image
    if player.get('skinInformation') and player['skinInformation'].get('IconUrl'):
        embed.set_thumbnail(url=player['skinInformation']['IconUrl'])
    
    # User ID
    embed.add_field(name="🆔 User ID", value=f"`{player.get('userId', 'N/A')}`", inline=False)
    
    embed.set_footer(text="- made by sagar")
    
    return embed

# EMBED 2: ONLY USERNAME HISTORY
async def create_history_embed(player: Dict) -> discord.Embed:
    """Create embed with ONLY username history (shows as many as possible)"""
    
    current_name = player.get('userName', 'Unknown')
    history = player.get('usernameHistory', [])
    
    # If no history or only current name
    if not history or len(history) <= 1:
        embed = discord.Embed(
            title=f"📝 Username History for {current_name}",
            description="This player has no username history or it's not available.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="They've always had this username!")
        return embed
    
    # Create embed
    embed = discord.Embed(
        title=f"📝 Username History",
        description=f"**Current:** {current_name}\n**Total name changes:** {len(history)}",
        color=discord.Color.purple()
    )
    
    #  history sequential 
    if current_name in history:
        history_without_current = [name for name in history if name != current_name]
        sequential_history = history_without_current + [current_name]
    else:
        sequential_history = history
    

    history_text = ""
    chunk_count = 1
    max_field_length = 1024
    
    for i, name in enumerate(sequential_history, 1):
        line = f"{i}. {name}"
        if name == current_name:
            line = f"**{i}. {name}** <- CURRENT\n"
        else:
            line = f"{i}. {name}\n"
        
        
        if len(history_text) + len(line) > max_field_length - 100:  # Leave buffer
            embed.add_field(
                name=f"Name History (Part {chunk_count})", 
                value=history_text, 
                inline=False
            )
            history_text = line
            chunk_count += 1
        else:
            history_text += line
    
    # Add the last chunk
    if history_text:
        embed.add_field(
            name=f"Name History (Part {chunk_count})", 
            value=history_text, 
            inline=False
        )
    
    # Add stats
    unique_names = len(set(history))
    if unique_names < len(history):
        embed.add_field(
            name="🔄 Note",
            value=f"Some names were used multiple times ({len(history) - unique_names} repeats)",
            inline=False
        )
    
    embed.set_footer(text=f"Showing {len(sequential_history)} names in {chunk_count}")
    
    return embed

@bot.event
async def on_ready():
    print(f"🎮 {bot.user} is ready!")
    print(f"🌐 Connected to {len(bot.guilds)} servers")
    
    # Force sync commands
    await bot.tree.sync()
    print("✅ Commands synced!")
    
    # List commands
    commands = await bot.tree.fetch_commands()
    command_names = [cmd.name for cmd in commands]
    print(f"📋 Registered commands: {command_names}")
    
    # Set status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="playing StumbleGuys"
        )
    )

if __name__ == "__main__":

    if not STUMBLE_KEY or STUMBLE_KEY == "your_actual_key_here" or len(STUMBLE_KEY) < 10:
        print("❌  key not found in .env file!")
        exit(1)
    
    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_actual_token_here" or len(DISCORD_TOKEN) < 20:
        print("❌ token not found .env file!")
       
        exit(1)
    
    print("✅ Keys loaded successfully from .env!")
    print(f"🔑 API Key: {STUMBLE_KEY[:5]}...{STUMBLE_KEY[-5:]}")
    
    bot.run(DISCORD_TOKEN)
    