"""Usage: !userinfo (or !userinfo @someone to check a mentioned user)"""


async def run(client, message, args):
    """Shows info about you or a mentioned user"""
    target = message.mentions[0] if message.mentions else message.author

    lines = [
        f"**{target}**",
        f"ID: `{target.id}`",
        f"Account created: {target.created_at.strftime('%Y-%m-%d')}",
    ]

    if message.guild:
        member = message.guild.get_member(target.id)
        if member and member.joined_at:
            lines.append(f"Joined this server: {member.joined_at.strftime('%Y-%m-%d')}")

    await message.channel.send("\n".join(lines))
