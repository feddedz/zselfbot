"""Usage: !purge 10  -> deletes your last 10 messages in this channel (max 50)"""

import asyncio


async def run(client, message, args):
    """Deletes your own last N messages in this channel (max 50)"""
    try:
        count = int(args.strip())
    except ValueError:
        await message.channel.send("Usage: `!purge 10` (a number, max 50)")
        return

    count = max(1, min(count, 50))
    deleted = 0

    async for msg in message.channel.history(limit=200):
        if deleted >= count:
            break
        if msg.author.id != client.user.id:
            continue
        try:
            await msg.delete()
            deleted += 1
            await asyncio.sleep(0.6)  # stay well under Discord's rate limits
        except Exception:
            continue

    confirmation = await message.channel.send(f"Deleted {deleted} message(s).")
    await asyncio.sleep(3)
    try:
        await confirmation.delete()
    except Exception:
        pass
