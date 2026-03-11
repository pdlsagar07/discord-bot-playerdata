# made by sagar
# the x-key used as stumble_key is provided by stumblelabs

import discord
from discord import app_commands
import requests
from datetime import datetime
from typing import Optional, Dict
import os
import time
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
    
    def search_by_username(self, username: str, retry_count: int = 2) -> Optional[Dict]:
        """Search for a player by username  - preserves exact username with symbols"""
        
        # Only trim whitespace - keep all symbols
        username = username.strip()
        
        # Try exact username first, then variations as fallback
        search_attempts = [
            username,  # Exact username
            username.lower(),  # Lowercase fallback
            username.title(),  # Title case fallback
            username.upper(),  # Uppercase fallback
        ]
        
        # Remove duplicates but keep order
        seen = set()
        search_attempts = [x for x in search_attempts if not (x in seen or seen.add(x))]
        
        for attempt_num in range(retry_count + 1):
            for attempt_username in search_attempts:
                try:
                    response = self.session.post(
                        f"{self.base_url}/users/search",
                        json={"username": attempt_username},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success') and data.get('data'):
                            return data.get('data')
                    
                    elif response.status_code == 429:
                        time.sleep(2)
                    
                except Exception as e:
                    print(f"Search attempt failed for {attempt_username}: {e}")
                    pass
            
            if attempt_num < retry_count:
                time.sleep(1)
        
        return None
    
    def search_by_user_id(self, user_id: str, retry_count: int = 2) -> Optional[Dict]:
        """Search for a player by user ID"""
        
        # Clean the user ID - remove any quotes and trim whitespace
        user_id = user_id.strip().strip('"\'')
        
        for attempt_num in range(retry_count + 1):
            try:
                # Try direct fetch by ID first (most efficient)
                response = self.session.get(
                    f"{self.base_url}/users/{user_id}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('data'):
                        return data.get('data')
                
                # If direct fetch fails, try searching with ID as username (fallback)
                elif response.status_code == 404:
                    search_response = self.session.post(
                        f"{self.base_url}/users/search",
                        json={"username": user_id},
                        timeout=10
                    )
                    
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        if search_data.get('success') and search_data.get('data'):
                            # Verify that the returned user has matching ID
                            player_data = search_data.get('data')
                            if player_data.get('userId') == user_id:
                                return player_data
                
                elif response.status_code == 429:
                    time.sleep(2)
                
            except Exception as e:
                print(f"Search by ID failed for {user_id}: {e}")
                pass
            
            if attempt_num < retry_count:
                time.sleep(1)
        
        return None
    
    #not sure if this ranked system works: 
def get_rank_info(tier_id: int, division_id: int | None = None) -> str:
    tiers = {
        0: "Unranked",
        1: "Wood",
        2: "Bronze",
        3: "Silver",
        4: "Gold",
        5: "Platinum",
        6: "Master",
        7: "Champion"
    }

    tier = tiers.get(tier_id, "Unknown")

    if tier in ["Unranked", "Champion"] or division_id is None:
        return tier

    divisions = {
        1: "I",
        2: "II",
        3: "III"
    }

    return f"{tier} {divisions.get(division_id, '')}".strip()

def format_season(season_str: str) -> str:
    """Convert 'LIVE_RANKED_SEASON_19' to 'S19'"""
    if season_str and "SEASON_" in season_str:
        try:
            season_num = season_str.split("SEASON_")[-1]
            return f"S{season_num}"
        except:
            return season_str
    return season_str

# Create bot instance
class StumbleBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = False
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.api = StumbleLabsAPI(STUMBLE_KEY)

bot = StumbleBot()

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
                description=f"No player found with username `{username}`\n\n**Tips:**\n• Make sure the username is spelled correctly\n• Wait a few seconds and try again",
                color=discord.Color.red()
            )
            embed.set_footer(text="If the problem persists, the API might be experiencing issues")
            await interaction.followup.send(embed=embed)
            return
        
        embed = await create_player_embed(player, username, interaction)
        await interaction.followup.send(embed=embed)

# COMMAND 2: /usernamehistory - Shows ONLY username history 
@bot.tree.command(name="usernamehistory", description="View username history")
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
                description=f"No player found with username `{username}`\n\n**Tips:**\n• Make sure the username is spelled correctly\n• Try using their exact username (case-sensitive)\n• The player might have changed their name recently",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = await create_history_embed(player)
        await interaction.followup.send(embed=embed)

# COMMAND 3: /userid - Search by user ID
@bot.tree.command(name="userid", description="Get Stumble Guys player data by user ID")
@app_commands.describe(user_id="The Stumble Guys user ID to search for")
@app_commands.guild_only()
async def userid_command(interaction: discord.Interaction, user_id: str):
    if interaction.guild is None:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    async with interaction.channel.typing():
        player = bot.api.search_by_user_id(user_id)
        
        if not player:
            embed = discord.Embed(
                title="❌ Player Not Found",
                description=f"No player found with user ID `{user_id}`\n\n**Tips:**\n• Make sure the user ID is correct\n• User IDs are usually numeric\n• The player might have changed their ID recently",
                color=discord.Color.red()
            )
            embed.set_footer(text="If the problem persists, the API might be experiencing issues")
            await interaction.followup.send(embed=embed)
            return
        
        embed = await create_player_embed(player, f"ID: {user_id}", interaction)
        await interaction.followup.send(embed=embed)
 
async def create_player_embed(player: Dict, searched_username: str, interaction: discord.Interaction) -> discord.Embed:
    """Create embed with L-shaped symbols and gray opacity effect"""
    
    player_name = player.get('userName', searched_username)
    
    embed = discord.Embed(
        title=f"**Sagar's Search Api**",
        color=discord.Color.blue()
    )
    
    # Skin image 
    if player.get('skinInformation') and player['skinInformation'].get('IconUrl'):
        embed.set_thumbnail(url=player['skinInformation']['IconUrl'])
    
    description = []
    
    user_id = player.get('userId', 'N/A')
     
    description.append(f"*ID*")
    description.append(f" └─ {user_id}")
     
    description.append(f"*Username*")
    description.append(f"  └─ {player_name}")
     
    # Country with flag
    country = player.get('country', 'Unknown')
    flag_map = {
    'AF': '🇦🇫', 'AL': '🇦🇱', 'DZ': '🇩🇿', 'AS': '🇦🇸', 'AD': '🇦🇩',
    'AO': '🇦🇴', 'AI': '🇦🇮', 'AQ': '🇦🇶', 'AG': '🇦🇬', 'AR': '🇦🇷',
    'AM': '🇦🇲', 'AW': '🇦🇼', 'AU': '🇦🇺', 'AT': '🇦🇹', 'AZ': '🇦🇿',
    'BS': '🇧🇸', 'BH': '🇧🇭', 'BD': '🇧🇩', 'BB': '🇧🇧', 'BY': '🇧🇾',
    'BE': '🇧🇪', 'BZ': '🇧🇿', 'BJ': '🇧🇯', 'BM': '🇧🇲', 'BT': '🇧🇹',
    'BO': '🇧🇴', 'BA': '🇧🇦', 'BW': '🇧🇼', 'BR': '🇧🇷', 'BN': '🇧🇳',
    'BG': '🇧🇬', 'BF': '🇧🇫', 'BI': '🇧🇮', 'KH': '🇰🇭', 'CM': '🇨🇲',
    'CA': '🇨🇦', 'CV': '🇨🇻', 'CF': '🇨🇫', 'TD': '🇹🇩', 'CL': '🇨🇱',
    'CN': '🇨🇳', 'CO': '🇨🇴', 'KM': '🇰🇲', 'CG': '🇨🇬', 'CD': '🇨🇩',
    'CR': '🇨🇷', 'CI': '🇨🇮', 'HR': '🇭🇷', 'CU': '🇨🇺', 'CY': '🇨🇾',
    'CZ': '🇨🇿', 'DK': '🇩🇰', 'DJ': '🇩🇯', 'DM': '🇩🇲', 'DO': '🇩🇴',
    'EC': '🇪🇨', 'EG': '🇪🇬', 'SV': '🇸🇻', 'GQ': '🇬🇶', 'ER': '🇪🇷',
    'EE': '🇪🇪', 'SZ': '🇸🇿', 'ET': '🇪🇹', 'FJ': '🇫🇯', 'FI': '🇫🇮',
    'FR': '🇫🇷', 'GA': '🇬🇦', 'GM': '🇬🇲', 'GE': '🇬🇪', 'DE': '🇩🇪',
    'GH': '🇬🇭', 'GR': '🇬🇷', 'GD': '🇬🇩', 'GT': '🇬🇹', 'GN': '🇬🇳',
    'GW': '🇬🇼', 'GY': '🇬🇾', 'HT': '🇭🇹', 'HN': '🇭🇳', 'HU': '🇭🇺',
    'IS': '🇮🇸', 'IN': '🇮🇳', 'ID': '🇮🇩', 'IR': '🇮🇷', 'IQ': '🇮🇶',
    'IE': '🇮🇪', 'IL': '🇮🇱', 'IT': '🇮🇹', 'JM': '🇯🇲', 'JP': '🇯🇵',
    'JO': '🇯🇴', 'KZ': '🇰🇿', 'KE': '🇰🇪', 'KI': '🇰🇮', 'KP': '🇰🇵',
    'KR': '🇰🇷', 'KW': '🇰🇼', 'KG': '🇰🇬', 'LA': '🇱🇦', 'LV': '🇱🇻',
    'LB': '🇱🇧', 'LS': '🇱🇸', 'LR': '🇱🇷', 'LY': '🇱🇾', 'LI': '🇱🇮',
    'LT': '🇱🇹', 'LU': '🇱🇺', 'MG': '🇲🇬', 'MW': '🇲🇼', 'MY': '🇲🇾',
    'MV': '🇲🇻', 'ML': '🇲🇱', 'MT': '🇲🇹', 'MH': '🇲🇭', 'MR': '🇲🇷',
    'MU': '🇲🇺', 'MX': '🇲🇽', 'FM': '🇫🇲', 'MD': '🇲🇩', 'MC': '🇲🇨',
    'MN': '🇲🇳', 'ME': '🇲🇪', 'MA': '🇲🇦', 'MZ': '🇲🇿', 'MM': '🇲🇲',
    'NA': '🇳🇦', 'NR': '🇳🇷', 'NP': '🇳🇵', 'NL': '🇳🇱', 'NZ': '🇳🇿',
    'NI': '🇳🇮', 'NE': '🇳🇪', 'NG': '🇳🇬', 'NO': '🇳🇴', 'OM': '🇴🇲',
    'PK': '🇵🇰', 'PW': '🇵🇼', 'PA': '🇵🇦', 'PG': '🇵🇬', 'PY': '🇵🇾',
    'PE': '🇵🇪', 'PH': '🇵🇭', 'PL': '🇵🇱', 'PT': '🇵🇹', 'QA': '🇶🇦',
    'RO': '🇷🇴', 'RU': '🇷🇺', 'RW': '🇷🇼', 'KN': '🇰🇳', 'LC': '🇱🇨',
    'VC': '🇻🇨', 'WS': '🇼🇸', 'SM': '🇸🇲', 'ST': '🇸🇹', 'SA': '🇸🇦',
    'SN': '🇸🇳', 'RS': '🇷🇸', 'SC': '🇸🇨', 'SL': '🇸🇱', 'SG': '🇸🇬',
    'SK': '🇸🇰', 'SI': '🇸🇮', 'SB': '🇸🇧', 'SO': '🇸🇴', 'ZA': '🇿🇦',
    'SS': '🇸🇸', 'ES': '🇪🇸', 'LK': '🇱🇰', 'SD': '🇸🇩', 'SR': '🇸🇷',
    'SE': '🇸🇪', 'CH': '🇨🇭', 'SY': '🇸🇾', 'TW': '🇹🇼', 'TJ': '🇹🇯',
    'TZ': '🇹🇿', 'TH': '🇹🇭', 'TL': '🇹🇱', 'TG': '🇹🇬', 'TO': '🇹🇴',
    'TT': '🇹🇹', 'TN': '🇹🇳', 'TR': '🇹🇷', 'TM': '🇹🇲', 'UG': '🇺🇬',
    'UA': '🇺🇦', 'AE': '🇦🇪', 'GB': '🇬🇧', 'US': '🇺🇸', 'UY': '🇺🇾',
    'UZ': '🇺🇿', 'VU': '🇻🇺', 'VE': '🇻🇪', 'VN': '🇻🇳', 'YE': '🇾🇪',
    'ZM': '🇿🇲', 'ZW': '🇿🇼'
}
    flag = flag_map.get(country, '🌐')
     
    description.append(f"*Country*")
    description.append(f"  └─ {flag}")
     
    # Trophies
    trophies = player.get('trophies', 0)
     
    description.append(f"*Trophies*")
    description.append(f"  └─ {trophies:,} 🏅")
     
    # Crowns
    crowns = player.get('crowns', 0)
     
    description.append(f"*crowns*")
    description.append(f"  └─ {crowns:,} 🏆")
     
    # Skin
    if player.get('skinInformation'):
        skin = player['skinInformation'].get('FriendlyName', 'Unknown')
    else:
        skin = player.get('skin', 'Unknown')
     
    description.append(f"*Skin*")
    description.append(f"  └─ {skin}")
     
    # Experience and Level
    exp = player.get('experience', 0)
    description.append(f"*Experience*")
    description.append(f"  └─{exp:,} ")
     
    # Online status
    status = ":green_circle:" if player.get('isOnline') else ":red_circle:"
     
    description.append(f"*Online*")
    description.append(f"  └─ {status}")
     
    # Rank info
    if player.get('ranked'):
        rank = player['ranked']
        rank_id = rank.get('currentRankId', 0)
        season = format_season(rank.get('currentSeasonId', 'Unknown'))
        rank_name = get_rank_info(rank_id)
         
        description.append(f"*Rank*")
        description.append(f"  └─ {rank_name} ({season})")
         
    # Clan if exists
    if player.get('clan'):
        clan = player['clan']
        clan_name = clan.get('name', 'Unknown')
        clan_tag = clan.get('tag', '???')
         
        description.append(f"*Clan*")
        description.append(f"    └─ {clan_name} [{clan_tag}]")
         
    embed.description = "\n".join(description)
    
    # Username history 
    if player.get('usernameHistory') and len(player['usernameHistory']) > 1:
        history = player.get('usernameHistory', [])
        recent_history = history[-5:] if len(history) > 5 else history
        current_name = player.get('userName', '')
        
        history_lines = []
        
        history_lines.append(f"*Username History*")
        
        for i, name in enumerate(recent_history, 1):
            if name == current_name:
                if i == len(recent_history):
                    history_lines.append(f"    └─  {name} (current)")
                else:
                    history_lines.append(f"    └─  {name} (current)")
            else:
                if i == len(recent_history):
                    history_lines.append(f"    └─  {name}")
                else:
                    history_lines.append(f"    └─  {name}")
        
        if len(history) > 5:
            history_lines.append(f"... and more")
        
        embed.add_field(
            name="", 
            value="\n".join(history_lines), 
            inline=False
        )
    
    embed.set_footer(text=f"Requested by {interaction.user.display_name}")
    
    return embed

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
    
    # last chunk
    if history_text:
        embed.add_field(
            name=f"Name History (Part {chunk_count})", 
            value=history_text, 
            inline=False
        )
    
    # stats
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
    
    await bot.tree.sync()
    print("✅ Commands synced!")
    
    commands = await bot.tree.fetch_commands()
    command_names = [cmd.name for cmd in commands]
    print(f"📋 Registered commands: {command_names}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Stumble Guys"
        )
    )

if __name__ == "__main__":
    if not STUMBLE_KEY or STUMBLE_KEY == "your_actual_key_here" or len(STUMBLE_KEY) < 10:
        print("❌ key not found in .env file!")
        exit(1)
    
    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_actual_token_here" or len(DISCORD_TOKEN) < 20:
        print("❌ token not found .env file!")
        exit(1)
    
    print("✅ Keys loaded successfully from .env!")
    print(f"🔑 API Key: {STUMBLE_KEY[:5]}...{STUMBLE_KEY[-5:]}")

# to deploy
from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
@app.route('/health')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


Thread(target=run_web, daemon=True).start()

bot.run(DISCORD_TOKEN)
