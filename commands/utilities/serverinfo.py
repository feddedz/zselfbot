"""Usage: !serverinfo"""


async def run(client, message, args):
    """Shows info about the current server"""
    guild = message.guild
    if not guild:
        await message.channel.send("This isn't a server channel.")
        return

    lines = [
        f"**{guild.name}**",
        f"ID: `{guild.id}`",
        f"Members: {guild.member_count}",
        f"Created: {guild.created_at.strftime('%Y-%m-%d')}",
        f"Owner ID: `{guild.owner_id}`",
    ]
    await message.channel.send("\n".join(lines))
