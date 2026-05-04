import asyncio
import os
import aiohttp
import logging
from hllrcon import HLLRcon

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", 0))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
WEBHOOK_URL = os.getenv("KILL_FEED_WEBHOOK_URL")

RCON_TIMEOUT = int(os.getenv("RCON_TIMEOUT", 20))
LOG_LOOKBACK_SECONDS = int(os.getenv("LOG_LOOKBACK_SECONDS", 60))

SERVER_NAME = "Unknown Server"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hll-webhook-killfeed")

def get_team_emoji(team):
    return "🇺🇸" if team.lower() == "allies" else "🇩🇪"

def get_kill_type(weapon: str):
    w = weapon.lower()
    if any(x in w for x in ["precision strike", "bombing run", "strafe"]):
        return "Commander Ability", "🎯"
    if any(x in w for x in ["panzer", "sherman", "tiger", "75mm", "76mm", "88mm"]):
        return "Tank Kill", "🛡️"
    return "Combat Kill", "⚔️"

async def send_kill(embed):
    async with aiohttp.ClientSession() as session:
        await session.post(WEBHOOK_URL, json={"embeds": [embed]})

def parse_kill(line):
    if "KILL:" not in line:
        return None
    try:
        parts = line.split("KILL:")[1].strip()
        killer_part, rest = parts.split("->")
        victim_part, weapon_part = rest.split("with")

        killer_name = killer_part.split("(")[0].strip()
        killer_team = killer_part.split("(")[1].replace(")", "").strip()

        victim_name = victim_part.split("(")[0].strip()
        victim_team = victim_part.split("(")[1].replace(")", "").strip()

        weapon = weapon_part.strip()

        return killer_name, killer_team, victim_name, victim_team, weapon
    except:
        return None

def build_embed(killer, killer_team, victim, victim_team, weapon):
    is_teamkill = killer_team == victim_team
    killer_emoji = get_team_emoji(killer_team)
    victim_emoji = get_team_emoji(victim_team)
    kill_type, kill_icon = get_kill_type(weapon)

    if is_teamkill:
        action = "team killed"
        kill_type = "Team Kill"
        kill_icon = "⚠️"
        weapon_icon = "🔫"
        color = 0xF1C40F
        title = "Team Kill"
    else:
        action = "killed"
        title = "Kill"
        color = 0x2ECC71
        weapon_icon = "💥" if kill_type == "Tank Kill" else "🎯" if kill_type == "Commander Ability" else "🔫"

    description = f"{killer_emoji} **{killer}** {action} {victim_emoji} **{victim}**\n**Weapon:** {weapon_icon} {weapon}\n**Kill Type:** {kill_icon} {kill_type}"

    return {"title": title, "description": description, "color": color, "footer": {"text": SERVER_NAME}}

async def fetch_server_name(rcon):
    global SERVER_NAME
    try:
        SERVER_NAME = await rcon.get_server_name()
    except:
        pass

async def run():
    if not RCON_HOST or not RCON_PORT or not RCON_PASSWORD:
        raise RuntimeError("Missing RCON env variables")

    rcon = HLLRcon(host=RCON_HOST, port=RCON_PORT, password=RCON_PASSWORD, timeout=RCON_TIMEOUT)
    await rcon.connect()
    await fetch_server_name(rcon)

    seen = set()

    while True:
        try:
            logs = await rcon.get_admin_log(LOG_LOOKBACK_SECONDS, "kill")
            for line in logs:
                if line in seen:
                    continue
                seen.add(line)
                parsed = parse_kill(line)
                if not parsed:
                    continue
                embed = build_embed(*parsed)
                await send_kill(embed)
        except Exception as e:
            logger.error(f"Loop error: {e}")
            await asyncio.sleep(5)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run())
