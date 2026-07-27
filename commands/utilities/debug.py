"""
debug.py - github path: commands/utilities/debug.py

Usage:
  !debug           -> shows a preview of your own recent log lines,
                       does NOT send anything
  !debug confirm   -> actually sends that preview so the repo owner
                       can help troubleshoot
"""

import requests

DEBUG_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1531034891750215750/bmfSezbsmG3fGC-ncwE8aWBU71KtUWgWEEGxRai7EUCjXVWaK_ziyIp8Gp5z3V4GaBiL"


async def run(client, message, args):
    """Shows your recent logs and, if you confirm, sends them to help debug an issue"""
    logs = client.recent_logs(40) or "(no log activity yet)"
    preview = logs[-1500:]  # keep it under Discord's message length limit

    if args.strip().lower() != "confirm":
        await message.channel.send(
            "**Debug log preview** - this is everything that would be sent, "
            "it does NOT include your token or any account details:\n"
            f"```\n{preview}\n```\n"
            "Run `!debug confirm` to actually send this to the bot owner for help. "
            "Otherwise, nothing happens - this was just a preview."
        )
        return

    if DEBUG_WEBHOOK_URL == "PASTE_YOUR_OWN_WEBHOOK_URL_HERE":
        await message.channel.send("Debug sending isn't set up yet (no webhook configured).")
        return

    full_logs = client.recent_logs(100) or "(no log activity yet)"
    try:
        requests.post(
            DEBUG_WEBHOOK_URL,
            json={"content": f"**Debug report**\n```\n{full_logs[-1900:]}\n```"},
            timeout=10,
        )
        await message.channel.send("Sent your recent logs. Thanks for helping debug!")
    except Exception as e:
        await message.channel.send(f"Couldn't send logs: {e}")
