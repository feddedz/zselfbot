"""Usage: !choose pizza, tacos, sushi"""

import random


async def run(client, message, args):
    """Picks randomly from a comma-separated list"""
    options = [o.strip() for o in args.split(",") if o.strip()]

    if len(options) < 2:
        await message.channel.send("Give me at least 2 options, comma-separated: `!choose a, b, c`")
        return

    await message.channel.send(f"🎯 I choose: **{random.choice(options)}**")
