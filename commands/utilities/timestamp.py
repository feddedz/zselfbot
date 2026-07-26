"""Usage: !timestamp (current time) or !timestamp 1735689600 (a unix timestamp)"""

import time


async def run(client, message, args):
    """Converts a unix timestamp (or now) into Discord's clickable time format"""
    args = args.strip()

    if args:
        try:
            unix = int(args)
        except ValueError:
            await message.channel.send("That's not a valid unix timestamp (whole number of seconds).")
            return
    else:
        unix = int(time.time())

    lines = [
        f"Short: <t:{unix}:t>",
        f"Long: <t:{unix}:F>",
        f"Relative: <t:{unix}:R>",
        f"Raw: `{unix}`",
    ]
    await message.channel.send("\n".join(lines))
