"""Usage: !8ball will it rain tomorrow?"""

import random

_ANSWERS = [
    "It is certain.", "Without a doubt.", "Yes, definitely.",
    "You may rely on it.", "As I see it, yes.", "Most likely.",
    "Outlook good.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.",
    "Better not tell you now.", "Cannot predict now.",
    "Don't count on it.", "My reply is no.",
    "My sources say no.", "Outlook not so good.", "Very doubtful.",
]


async def run(client, message, args):
    """Ask the magic 8-ball a question"""
    if not args.strip():
        await message.channel.send("Ask a question first: `!8ball will it rain tomorrow?`")
        return
    await message.channel.send(f"🎱 {random.choice(_ANSWERS)}")
