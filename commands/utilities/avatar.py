"""Usage: !avatar (or !avatar @someone)"""


async def run(client, message, args):
    """Sends the avatar URL for you or a mentioned user"""
    target = message.mentions[0] if message.mentions else message.author
    await message.channel.send(f"{target}'s avatar: {target.display_avatar.url}")
