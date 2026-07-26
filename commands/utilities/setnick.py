"""
setnick.py - example command showing how to use client.storage.
Push this to your repo under commands/utilities/setnick.py (or wherever)
if you want it, or just use it as a template for your own commands.

Usage: !setnick CoolName  -> saves it
       !setnick            -> shows the saved value
"""


async def run(client, message, args):
    """Saves or shows a custom nickname (example of using storage)"""
    args = args.strip()

    if args:
        client.storage.set("nickname", args)
        await message.channel.send(f"Saved nickname: {args}")
    else:
        current = client.storage.get("nickname", "no nickname set yet")
        await message.channel.send(f"Current nickname: {current}")
