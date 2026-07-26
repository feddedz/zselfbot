"""Usage: !rdap example.com or !rdap 8.8.8.8

RDAP lookup (rdap.org) summarizing key fields. Caches results.
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


async def _fetch_json(url):
    def _f():
        with urllib.request.urlopen(url, timeout=12) as r:
            return r.read()
    data = await asyncio.to_thread(_f)
    return json.loads(data)


async def run(client, message, args):
    """RDAP lookup for domain or IP. Usage: !rdap <domain_or_ip>"""
    target = args.strip()
    if not target:
        await message.channel.send("Usage: `!rdap <domain_or_ip>`")
        return

    key = f"osint:rdap:{target}"
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
        obj = await _fetch_json(url)
    except Exception as e:
        await message.channel.send(f"RDAP request failed: {e}")
        return

    lines = [f"**RDAP: {target}**"]
    if obj.get("handle"):
        lines.append(f"Handle: `{obj.get('handle')}`")
    if obj.get("name"):
        lines.append(f"Name: {obj.get('name')}")
    # IP ranges
    if obj.get("startAddress") or obj.get("startAddress"):
        lines.append(f"Range: {obj.get('startAddress','?')} - {obj.get('endAddress','?')}")

    if obj.get("entities"):
        ent_lines = []
        for ent in obj.get("entities", [])[:6]:
            # try vcard fn
            name = None
            v = ent.get("vcardArray")
            if v and len(v) > 1:
                for item in v[1]:
                    if item and item[0] == "fn":
                        name = item[3]
                        break
            if not name:
                name = ent.get("handle") or ",".join(ent.get("roles", []))
            if name:
                ent_lines.append(str(name))
        if ent_lines:
            lines.append("Entities: " + ", ".join(ent_lines))

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
