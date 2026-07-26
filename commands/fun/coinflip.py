"""Usage: !coinflip"""

import random


async def run(client, message, args):
    """Flips a coin"""
    await message.channel.send(f"🪙 {random.choice(['Heads', 'Tails'])}")
