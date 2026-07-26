"""
help.py - lives at commands/help.py in your repo.
Everyone's exe downloads this automatically, so editing THIS FILE on
GitHub is all it takes to restyle help for everyone. No exe rebuild.

Uses client.loaded_commands (every command + its category) and
client.info_text (whatever you put in your repo's info.txt) to build
a Discord embed instead of plain text.
"""

import discord

EMBED_COLOR = 0x8A2BE2  # change this hex to reskin the whole thing


async def run(client, message, args):
    """Shows commands and categories, or details on one"""
    prefix = client.cfg["prefix"]
    target = args.strip().lower()

    categories = {}
    for name, info in client.loaded_commands.items():
        categories.setdefault(info["category"], []).append(name)

    # !help  -> overview embed
    if not target:
        embed = discord.Embed(
            title="📖 Command Help",
            description=client.info_text or "No announcements right now.",
            color=EMBED_COLOR,
        )
        for cat in sorted(categories):
            names = ", ".join(f"`{n}`" for n in sorted(categories[cat]))
            embed.add_field(name=f"📁 {cat} ({len(categories[cat])})", value=names, inline=False)
        embed.set_footer(text=f"Prefix: {prefix}  |  Try {prefix}help <category> or {prefix}help <command>")
        await message.channel.send(embed=embed)
        return

    # !help <category>
    if target in categories:
        embed = discord.Embed(title=f"📁 {target}", color=EMBED_COLOR)
        for name in sorted(categories[target]):
            doc = (client.loaded_commands[name]["module"].run.__doc__ or "No description").strip()
            embed.add_field(name=f"{prefix}{name}", value=doc, inline=False)
        await message.channel.send(embed=embed)
        return

    # !help <command>
    info = client.loaded_commands.get(target)
    if info:
        doc = (info["module"].run.__doc__ or "No description").strip()
        embed = discord.Embed(title=f"{prefix}{target}", description=doc, color=EMBED_COLOR)
        embed.set_footer(text=f"Category: {info['category']}")
        await message.channel.send(embed=embed)
        return

    embed = discord.Embed(
        description=f"No command or category called `{target}`.",
        color=0xFF5555,
    )
    await message.channel.send(embed=embed)
