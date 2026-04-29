from __future__ import annotations

import logging
import os
from collections import deque

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from hll_client import HLLClient, HLLConfig, stringify_response
from kill_feed import KillEvent, parse_kill_log

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hll-discord-rcon-bot")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
ADMIN_ROLE = os.getenv("DISCORD_ADMIN_ROLE", "").strip()
ENABLE_RAW_RCON = os.getenv("ENABLE_RAW_RCON", "false").lower() == "true"

HLL_HOST = os.getenv("HLL_RCON_HOST", "")
HLL_PORT = int(os.getenv("HLL_RCON_PORT", "0") or 0)
HLL_PASSWORD = os.getenv("HLL_RCON_PASSWORD", "")

KILL_FEED_ENABLED = os.getenv("KILL_FEED_ENABLED", "false").lower() == "true"
KILL_FEED_CHANNEL_ID = int(os.getenv("KILL_FEED_CHANNEL_ID", "0") or 0)
KILL_FEED_WEBHOOK_URL = os.getenv("KILL_FEED_WEBHOOK_URL", "").strip()
KILL_FEED_WEBHOOK_USERNAME = os.getenv("KILL_FEED_WEBHOOK_USERNAME", "HLL Kill Feed").strip() or "HLL Kill Feed"
KILL_FEED_POLL_SECONDS = max(5, int(os.getenv("KILL_FEED_POLL_SECONDS", "10") or 10))
KILL_FEED_LOOKBACK_MINUTES = max(1, int(os.getenv("KILL_FEED_LOOKBACK_MINUTES", "1") or 1))
KILL_FEED_INCLUDE_TEAM_KILLS = os.getenv("KILL_FEED_INCLUDE_TEAM_KILLS", "true").lower() == "true"
KILL_FEED_POST_STARTUP_BACKLOG = os.getenv("KILL_FEED_POST_STARTUP_BACKLOG", "false").lower() == "true"

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")
if not HLL_HOST or not HLL_PORT or not HLL_PASSWORD:
    raise RuntimeError("Missing HLL_RCON_HOST, HLL_RCON_PORT, or HLL_RCON_PASSWORD")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
hll = HLLClient(HLLConfig(host=HLL_HOST, port=HLL_PORT, password=HLL_PASSWORD))

_seen_kill_events: deque[str] = deque()
_seen_kill_event_set: set[str] = set()
_kill_feed_bootstrapped = False
_KILL_FEED_CACHE_LIMIT = 5000


def is_authorized(interaction: discord.Interaction) -> bool:
    perms = getattr(interaction.user, "guild_permissions", None)
    if perms and perms.administrator:
        return True
    if ADMIN_ROLE and isinstance(interaction.user, discord.Member):
        return any(role.name == ADMIN_ROLE for role in interaction.user.roles)
    return False


async def require_admin(interaction: discord.Interaction) -> bool:
    if is_authorized(interaction):
        return True
    await interaction.response.send_message(
        "You do not have permission to use this command.", ephemeral=True
    )
    return False


async def send_result(interaction: discord.Interaction, title: str, result) -> None:
    text = stringify_response(result)
    embed = discord.Embed(title=title, description=f"```{text}```")
    await interaction.followup.send(embed=embed, ephemeral=True)


def remember_kill_event(key: str) -> bool:
    if key in _seen_kill_event_set:
        return False
    while len(_seen_kill_events) >= _KILL_FEED_CACHE_LIMIT:
        old_key = _seen_kill_events.popleft()
        _seen_kill_event_set.discard(old_key)
    _seen_kill_events.append(key)
    _seen_kill_event_set.add(key)
    return True


def team_label(team: str) -> str:
    labels = {
        "Allies": "🟦 Allies",
        "Axis": "🟥 Axis",
        "None": "⬜ None",
    }
    return labels.get(team, team or "Unknown")


def build_kill_embed(event: KillEvent) -> discord.Embed:
    title = "⚠️ Team Kill" if event.is_team_kill else "💀 Kill"
    embed = discord.Embed(title=title)
    embed.add_field(
        name="Killer",
        value=f"**{event.killer}**\n{team_label(event.killer_team)}",
        inline=True,
    )
    embed.add_field(
        name="Killed",
        value=f"**{event.victim}**\n{team_label(event.victim_team)}",
        inline=True,
    )
    embed.add_field(name="Weapon", value=f"`{event.weapon}`", inline=False)
    if event.log_time:
        embed.set_footer(text=event.log_time)
    return embed


async def get_kill_feed_channel() -> discord.abc.Messageable | None:
    if not KILL_FEED_CHANNEL_ID:
        return None
    channel = bot.get_channel(KILL_FEED_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(KILL_FEED_CHANNEL_ID)
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        log.warning("KILL_FEED_CHANNEL_ID is not a text channel or thread: %s", KILL_FEED_CHANNEL_ID)
        return None
    return channel


async def send_kill_feed_embed(embed: discord.Embed) -> bool:
    """Send a kill feed embed to a webhook first, then fall back to a channel."""
    if KILL_FEED_WEBHOOK_URL:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(KILL_FEED_WEBHOOK_URL, session=session)
            await webhook.send(
                embed=embed,
                username=KILL_FEED_WEBHOOK_USERNAME,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        return True

    channel = await get_kill_feed_channel()
    if channel is None:
        return False
    await channel.send(embed=embed)
    return True


@tasks.loop(seconds=10.0)
async def kill_feed_loop() -> None:
    global _kill_feed_bootstrapped

    if not KILL_FEED_ENABLED or (not KILL_FEED_CHANNEL_ID and not KILL_FEED_WEBHOOK_URL):
        return

    try:
        raw_logs = await hll.show_log(KILL_FEED_LOOKBACK_MINUTES, "KILL")
        events = parse_kill_log(raw_logs)

        if not _kill_feed_bootstrapped:
            for event in events:
                remember_kill_event(event.key)
            _kill_feed_bootstrapped = True
            if not KILL_FEED_POST_STARTUP_BACKLOG:
                log.info("Kill feed bootstrapped with %d existing kill events; startup backlog skipped", len(events))
                return

        for event in events:
            if event.is_team_kill and not KILL_FEED_INCLUDE_TEAM_KILLS:
                continue
            if remember_kill_event(event.key):
                await send_kill_feed_embed(build_kill_embed(event))
    except Exception:
        log.exception("Kill feed polling failed")


@kill_feed_loop.before_loop
async def before_kill_feed_loop() -> None:
    await bot.wait_until_ready()


@bot.event
async def on_ready() -> None:
    log.info("Logged in as %s", bot.user)
    try:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            log.info("Synced %d guild commands", len(synced))
        else:
            synced = await bot.tree.sync()
            log.info("Synced %d global commands", len(synced))
    except Exception:
        log.exception("Slash command sync failed")

    if KILL_FEED_ENABLED:
        if not KILL_FEED_CHANNEL_ID and not KILL_FEED_WEBHOOK_URL:
            log.warning("KILL_FEED_ENABLED=true but neither KILL_FEED_WEBHOOK_URL nor KILL_FEED_CHANNEL_ID is set")
        elif not kill_feed_loop.is_running():
            kill_feed_loop.change_interval(seconds=float(KILL_FEED_POLL_SECONDS))
            kill_feed_loop.start()
            log.info(
                "Kill feed started: webhook=%s channel=%s poll=%ss lookback=%sm",
                bool(KILL_FEED_WEBHOOK_URL),
                KILL_FEED_CHANNEL_ID or "not set",
                KILL_FEED_POLL_SECONDS,
                KILL_FEED_LOOKBACK_MINUTES,
            )


@bot.tree.command(name="hll_ping", description="Check whether the Discord bot is online.")
async def hll_ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("HLL bot is online.", ephemeral=True)


@bot.tree.command(name="hll_status", description="Show HLL server information from RCON.")
async def hll_status(interaction: discord.Interaction) -> None:
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        result = await hll.get_server_info()
        await send_result(interaction, "HLL Server Status", result)
    except Exception as exc:
        log.exception("/hll_status failed")
        await interaction.followup.send(f"RCON status failed: `{exc}`", ephemeral=True)


@bot.tree.command(name="hll_players", description="List current players from HLL RCON.")
async def hll_players(interaction: discord.Interaction) -> None:
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        result = await hll.get_players()
        await send_result(interaction, "HLL Players", result)
    except Exception as exc:
        log.exception("/hll_players failed")
        await interaction.followup.send(f"RCON players failed: `{exc}`", ephemeral=True)


@bot.tree.command(name="hll_broadcast", description="Broadcast a message to the HLL server.")
@app_commands.describe(message="Message to display in game")
async def hll_broadcast(interaction: discord.Interaction, message: str) -> None:
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        result = await hll.broadcast(message)
        await send_result(interaction, "Broadcast Sent", result)
    except Exception as exc:
        log.exception("/hll_broadcast failed")
        await interaction.followup.send(f"RCON broadcast failed: `{exc}`", ephemeral=True)


@bot.tree.command(name="hll_kick", description="Kick a player by name or player ID.")
@app_commands.describe(player="Exact player name or Steam/EOS ID", reason="Kick reason")
async def hll_kick(interaction: discord.Interaction, player: str, reason: str = "Kicked by admin") -> None:
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        result = await hll.kick(player, reason)
        await send_result(interaction, "Kick Sent", result)
    except Exception as exc:
        log.exception("/hll_kick failed")
        await interaction.followup.send(f"RCON kick failed: `{exc}`", ephemeral=True)


@bot.tree.command(name="hll_killfeed_status", description="Show kill feed configuration and cache status.")
async def hll_killfeed_status(interaction: discord.Interaction) -> None:
    if not await require_admin(interaction):
        return
    status = (
        f"Enabled: {KILL_FEED_ENABLED}\n"
        f"Channel ID Fallback: {KILL_FEED_CHANNEL_ID or 'not set'}\n"
        f"Webhook URL Set: {bool(KILL_FEED_WEBHOOK_URL)}\n"
        f"Webhook Username: {KILL_FEED_WEBHOOK_USERNAME}\n"
        f"Poll Seconds: {KILL_FEED_POLL_SECONDS}\n"
        f"Lookback Minutes: {KILL_FEED_LOOKBACK_MINUTES}\n"
        f"Include Team Kills: {KILL_FEED_INCLUDE_TEAM_KILLS}\n"
        f"Post Startup Backlog: {KILL_FEED_POST_STARTUP_BACKLOG}\n"
        f"Loop Running: {kill_feed_loop.is_running()}\n"
        f"Seen Event Cache: {len(_seen_kill_events)}"
    )
    await interaction.response.send_message(f"```{status}```", ephemeral=True)


@bot.tree.command(name="hll_killfeed_test", description="Post a sample kill feed message to the configured channel.")
async def hll_killfeed_test(interaction: discord.Interaction) -> None:
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    if not KILL_FEED_WEBHOOK_URL and not KILL_FEED_CHANNEL_ID:
        await interaction.followup.send("Set KILL_FEED_WEBHOOK_URL or KILL_FEED_CHANNEL_ID first.", ephemeral=True)
        return
    sample_log = (
        "[00:00:01 hours (1234567890)] KILL: Example Tanker(Axis/123) "
        "-> Example Enemy(Allies/456) with PzKpfw IV"
    )
    sample_event = parse_kill_log(sample_log)[0]
    await send_kill_feed_embed(build_kill_embed(sample_event))
    destination = "webhook" if KILL_FEED_WEBHOOK_URL else "channel"
    await interaction.followup.send(f"Sample kill feed message sent via {destination}.", ephemeral=True)


@bot.tree.command(name="raw_rcon", description="Run a raw RCON command. Disabled unless ENABLE_RAW_RCON=true.")
@app_commands.describe(command="Raw RCON command")
async def raw_rcon(interaction: discord.Interaction, command: str) -> None:
    if not await require_admin(interaction):
        return
    if not ENABLE_RAW_RCON:
        await interaction.response.send_message(
            "Raw RCON is disabled. Set ENABLE_RAW_RCON=true in Railway Variables to enable it.",
            ephemeral=True,
        )
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        result = await hll.raw(command)
        await send_result(interaction, "Raw RCON Result", result)
    except Exception as exc:
        log.exception("/raw_rcon failed")
        await interaction.followup.send(f"Raw RCON failed: `{exc}`", ephemeral=True)


bot.run(DISCORD_TOKEN)
