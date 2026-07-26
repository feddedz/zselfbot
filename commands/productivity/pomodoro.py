"""Usage: !pomodoro 25 Start a 25-minute focus session"""

import asyncio

async def run(client, message, args):
    """Start a simple pomodoro timer (minutes). Not persistent across restarts."""
    try:
        minutes = int(args.strip() or "25")
    except ValueError:
        await message.channel.send("Usage: `!pomodoro 25` (minutes as integer)")
        return

    await message.channel.send(f"🍅 Pomodoro started for {minutes} minute(s). Focus!")
    async def _finish():
        await asyncio.sleep(minutes * 60)
        await message.channel.send("✅ Pomodoro complete! Take a break.")
    try:
        asyncio.create_task(_finish())
    except Exception:
        try:
            client.loop.create_task(_finish())
        except Exception:
            pass
