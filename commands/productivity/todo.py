"""Usage: !todo add Buy milk | !todo list | !todo rm 2"""


async def run(client, message, args):
    """Simple per-user todo: add/list/remove items (stored in client.storage)"""
    sub = args.strip()
    if not sub:
        await message.channel.send("Usage: `!todo add <item>` | `!todo list` | `!todo rm <index>`")
        return

    parts = sub.split(None, 1)
    cmd = parts[0].lower()
    user_key = f"todo:{message.author.id}"
    todos = client.storage.get(user_key, [])

    if cmd == "add" and len(parts) > 1:
        todos.append(parts[1].strip())
        client.storage.set(user_key, todos)
        await message.channel.send(f"Added todo #{len(todos)}: {parts[1].strip()}")
    elif cmd in ("list", "ls"):
        if not todos:
            await message.channel.send("You have no todos.")
            return
        lines = [f"Your todos ({len(todos)}):"]
        for i, t in enumerate(todos, 1):
            lines.append(f"{i}. {t}")
        await message.channel.send("\n".join(lines))
    elif cmd in ("rm", "remove", "del") and len(parts) > 1:
        try:
            idx = int(parts[1].strip())
            if 1 <= idx <= len(todos):
                item = todos.pop(idx-1)
                client.storage.set(user_key, todos)
                await message.channel.send(f"Removed todo #{idx}: {item}")
            else:
                await message.channel.send("Index out of range.")
        except ValueError:
            await message.channel.send("Invalid index. Use `!todo rm 2`.")
    else:
        await message.channel.send("Unknown todo command. Use add/list/rm.")
