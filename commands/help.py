"""
help.py - lives at commands/help.py in your repo.
Everyone's exe downloads this automatically, so editing THIS FILE on
GitHub is all it takes to restyle help for everyone. No exe rebuild.

Plain text only - self-bots (user accounts) can't send real Discord
embeds, only bot accounts and webhooks can, so this just uses basic
markdown (bold, code ticks) in a normal message.
"""


async def run(client, message, args):
    """Shows commands and categories, or details on one"""
    prefix = client.cfg["prefix"]
    target = args.strip().lower()

    categories = {}
    for name, info in client.loaded_commands.items():
        categories.setdefault(info["category"], []).append(name)

    # !help  -> overview
    if not target:
        lines = []
        if client.info_text:
            lines.append(client.info_text)
            lines.append("")
        lines.append(f"**Categories** (prefix: `{prefix}`)")
        for cat in sorted(categories):
            lines.append(f"`{cat}` - {len(categories[cat])} command(s)")
        lines.append("")
        lines.append(f"Type `{prefix}help <category>` or `{prefix}help <command>` for more.")
        await message.channel.send("\n".join(lines))
        return

    # !help <category>
    if target in categories:
        lines = [f"**{target}** commands:"]
        for name in sorted(categories[target]):
            doc = (client.loaded_commands[name]["module"].run.__doc__ or "No description").strip()
            lines.append(f"`{prefix}{name}` - {doc}")
        await message.channel.send("\n".join(lines))
        return

    # !help <command>
    info = client.loaded_commands.get(target)
    if info:
        doc = (info["module"].run.__doc__ or "No description").strip()
        await message.channel.send(f"`{prefix}{target}` ({info['category']}) - {doc}")
        return

    await message.channel.send(f"No command or category called `{target}`.")
