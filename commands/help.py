# ================================================================
# updated help.py – hides 'owner' category and its commands
# place at: commands/help.py
# ================================================================
"""
help.py - shows commands and categories, excluding 'owner' category.
"""
async def run(client, message, args):
    prefix = client.cfg["prefix"]
    target = args.strip().lower()

    categories = {}
    for name, info in client.loaded_commands.items():
        cat = info["category"]
        # Hide owner category from help
        if cat.lower() == "owner":
            continue
        categories.setdefault(cat, []).append(name)

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

    if target in categories:
        lines = [f"**{target}** commands:"]
        for name in sorted(categories[target]):
            doc = (client.loaded_commands[name]["module"].run.__doc__ or "No description").strip()
            lines.append(f"`{prefix}{name}` - {doc}")
        await message.channel.send("\n".join(lines))
        return

    # Check if it's a command (but skip owner commands)
    info = client.loaded_commands.get(target)
    if info and info["category"].lower() != "owner":
        doc = (info["module"].run.__doc__ or "No description").strip()
        await message.channel.send(f"`{prefix}{target}` ({info['category']}) - {doc}")
        return

    await message.channel.send(f"No command or category called `{target}`.")
