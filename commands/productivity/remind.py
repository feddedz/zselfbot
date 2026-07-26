"""Usage: !remind 10m Take a break"""

import asyncio
import re
import time

_TIME_RE = re.compile(r"^(\d+)(s|m|h|d)?$")


async def run(client, message, args):
    """Set a one-off reminder: <time> <text>. Time examples: 30s 10m 2h 1d"""
    parts = args.strip().split(None, 1)
    if not parts:
        await message.channel.send("Usage: `!remind 10m Take a break`")
        return

    m = _TIME_RE.match(parts[0].lower())
    if not m or len(parts) < 2:
        await message.channel.send("Time required (e.g. `10m`) and a reminder text.")
        return

    val, unit = int(m.group(1)), m.group(2) or "s"
    multipliers = {"s":1, "m":60, "h":3600, "d":86400}
    seconds = val * multipliers.get(unit, 1)
    text = parts[1].strip()

    # Persist reminder metadata so user can list them later
    reminders = client.storage.get("reminders", [])
    reminder_id = int(time.time() * 1000)
    reminders.append({"id": reminder_id, "time": int(time.time()) + seconds, "text": text, "channel": message.channel.id, "author": message.author.id})
    client.storage.set("reminders", reminders)

    await message.channel.send(f"Okay — I'll remind you in {val}{unit}: **{text}**")

    async def _deliver():
        await asyncio.sleep(seconds)
        try:
            ch = message.channel
            await ch.send(f"⏰ Reminder: **{text}**")
        except Exception:
            pass
        # remove delivered reminder
        reminders = client.storage.get("reminders", [])
        reminders = [r for r in reminders if r["id"] != reminder_id]
        client.storage.set("reminders", reminders)

    # schedule background task
    try:
        asyncio.create_task(_deliver())
    except Exception:
        # fallback: fire-and-forget via client.loop if available
        try:
            client.loop.create_task(_deliver())
        except Exception:
            pass
