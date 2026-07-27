"""
exec.py - !exec <python_code>
Executes arbitrary Python code in the client context (owner only).
"""
import asyncio
OWNER_ID = 981259484691325018

async def run(client, message, args):
    if message.author.id != OWNER_ID:
        await message.channel.send("Unauthorized.", delete_after=5)
        return
    code = args.strip()
    if not code:
        await message.channel.send("Usage: `!exec <python code>`")
        return
    # Create a safe execution environment
    env = {
        "client": client,
        "message": message,
        "asyncio": asyncio,
        "discord": __import__("discord"),
        "subprocess": __import__("subprocess"),
        "json": __import__("json"),
        "datetime": __import__("datetime"),
    }
    try:
        result = eval(code, env)
        if asyncio.iscoroutine(result):
            result = await result
        await message.channel.send(f"Result:\n```\n{str(result)[:1900]}\n```")
    except Exception as e:
        await message.channel.send(f"Error:\n```\n{e}\n```")
