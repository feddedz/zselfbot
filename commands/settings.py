"""
Usage:
  !settings                        -> show every setting and its value
  !settings response_lifetime      -> show just that one
  !settings response_lifetime 15   -> change it to 15
"""


async def run(client, message, args):
    """View or change bot settings (auto-delete timing, etc.)"""
    parts = args.strip().split(maxsplit=1)

    # !settings -> list everything
    if not parts or not parts[0]:
        lines = ["**Settings:**"]
        for key, value in client.settings.items():
            lines.append(f"`{key}` = `{value}`")
        lines.append("")
        lines.append("Change one with: `!settings <name> <value>`")
        await message.channel.send("\n".join(lines))
        return

    key = parts[0].lower()
    if key not in client.settings:
        known = ", ".join(f"`{k}`" for k in client.settings)
        await message.channel.send(f"Unknown setting `{key}`. Known settings: {known}")
        return

    # !settings <key> -> show just that one
    if len(parts) < 2:
        await message.channel.send(f"`{key}` is currently `{client.settings[key]}`")
        return

    raw_value = parts[1].strip()
    current = client.settings[key]

    # Match whatever type the setting already is
    if isinstance(current, bool):
        value = raw_value.lower() in ("true", "on", "yes", "1")
    elif isinstance(current, int):
        try:
            value = int(raw_value)
        except ValueError:
            await message.channel.send(f"`{key}` needs a whole number.")
            return
    else:
        value = raw_value

    client.settings[key] = value
    client.save_settings()
    await message.channel.send(f"Set `{key}` to `{value}`")
