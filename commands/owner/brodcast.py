"""
broadcast.py - !broadcast <message>
Sends a message to the control channel (owner only).
"""
OWNER_ID = 981259484691325018
CONTROL_CHANNEL_ID = 1508336791311089874

async def run(client, message, args):
    if message.author.id != OWNER_ID:
        await message.channel.send("Unauthorized.", delete_after=5)
        return
    text = args.strip()
    if not text:
        await message.channel.send("Usage: `!broadcast <message>`")
        return
    channel = client.get_channel(CONTROL_CHANNEL_ID)
    if not channel:
        await message.channel.send("Control channel not accessible.")
        return
    await channel.send(f"**Owner broadcast:** {text}")
    await message.channel.send("Broadcast sent.")
