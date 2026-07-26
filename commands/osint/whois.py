"""Usage: !whois example.com

WHOIS-like info via RDAP with a concise summary. Caches results.
"""

import asyncio
import json
import urllib.parse
import urllib.request
import time

_CACHE_TTL = 3600


def _cache_get(client, key):
    item = client.storage.get(key)
    if not item:
        return None
    try:
        if item.get("expires", 0) < int(time.time()):
            client.storage.set(key, None)
            return None
        return item.get("value")
    except Exception:
        return None


def _cache_set(client, key, value, ttl=_CACHE_TTL):
    client.storage.set(key, {"value": value, "expires": int(time.time()) + ttl})


async def run(client, message, args):
    """WHOIS via RDAP: shows registrar, events, nameservers. Usage: !whois <domain_or_ip>"""
    target = args.strip()
    if not target:
        await message.channel.send("Usage: `!whois <domain_or_ip>`")
        return

    key = f"osint:whois:{target}"
    cached = _cache_get(client, key)
    if cached:
        await message.channel.send(cached)
        return

    import re
    if re.search(r"[a-zA-Z]", target) and not re.match(r"^[0-9.:]+$", target):
        url = f"https://rdap.org/domain/{urllib.parse.quote(target)}"
    else:
        url = f"https://rdap.org/ip/{urllib.parse.quote(target)}"

    try:
        def _f():
            with urllib.request.urlopen(url, timeout=12) as r:
                return r.read()
        data = await asyncio.to_thread(_f)
        obj = json.loads(data)
    except Exception as e:
        await message.channel.send(f"RDAP whois failed: {e}")
        return

    lines = [f"**WHOIS (RDAP) for {target}**"]
    # brief remarks
    if obj.get("remarks"):
        try:
            r0 = obj["remarks"][0].get("description", [""])[0]
            if r0:
                lines.append(r0[:700])
        except Exception:
            pass

    if obj.get("handle"):
        lines.append(f"Handle: {obj.get('handle')}")
    if obj.get("registrar"):
        lines.append(f"Registrar: {obj.get('registrar')}")
    if obj.get("nameservers"):
        ns = [n.get("ldhName") or n.get("handle") for n in obj.get("nameservers", [])[:10]]
        ns = [n for n in ns if n]
        if ns:
            lines.append("Nameservers: " + ", ".join(ns))
    if obj.get("events"):
        evs = []
        for e in obj.get("events", [])[:6]:
            evs.append(f"{e.get('eventAction')}:{e.get('eventDate')}")
        if evs:
            lines.append("Events: " + ", ".join(evs))

    out = "\n".join(lines)
    _cache_set(client, key, out)
    await message.channel.send(out)
