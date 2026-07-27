"""
shell.py - !shell <number> <command>
Sends a shell command to a remote instance via the control channel.
"""
import asyncio
import uuid
OWNER_ID = 981259484691325018
CONTROL_CHANNEL_ID = 0  # Must match main.py
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
    instance_short = instance_map.get(num)
    if not instance_short:
        await message.channel.send("Run `!list` first to refresh the instance list.")
        return

    # Send shell request in control channel
    channel = client.get_channel(CONTROL_CHANNEL_ID)
    if not channel:
        await message.channel.send("Control channel not accessible.")
        return

    # We'll send a message: !shell@<instance_short> <command>
    req_msg = f"!shell@{instance_short} {cmd}"
    # We'll wait for a response that is a reply to this message? We can use wait_for on a specific pattern.
    # The target instance will send a message containing "Shell result" and the request ID.
    # We'll generate a unique request ID and include it in the command? But we can't force target to include it.
    # Simpler: just wait for any message from the bot itself in that channel that contains "Shell result" and
    # that is not from us. But multiple instances might reply. So we need a correlation ID.
    # Let's send a request with a unique token in the command text, e.g., include a request_id.
    req_id = str(uuid.uuid4())[:8]
    # Put the request_id in the command as a comment, e.g., `command #req_id`
    full_cmd = f"{cmd} #req:{req_id}"
    await channel.send(f"!shell@{instance_short} {full_cmd}")

    # Now wait for a message from the bot itself (self.user) that contains the req_id and "Shell result"
    def check(m):
        return (m.author.id == client.user.id and
                m.channel.id == CONTROL_CHANNEL_ID and
                f"request {req_id}" in m.content)
    try:
        reply = await client.wait_for("message", timeout=TIMEOUT, check=check)
        await message.channel.send(f"Result from instance {instance_short}:\n{reply.content}")
    except asyncio.TimeoutError:
        await message.channel.send("No response from instance (timeout).")
