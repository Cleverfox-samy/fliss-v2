from __future__ import annotations
import httpx
from config import get_settings


# ── Fast lookup for common UK locations ──────────────────────────────────────

UK_LOCATIONS = {
    "brighton": {"latitude": 50.8225, "longitude": -0.1372, "formatted_address": "Brighton, UK"},
    "hove": {"latitude": 50.8279, "longitude": -0.1681, "formatted_address": "Hove, Brighton and Hove, UK"},
    "london": {"latitude": 51.5074, "longitude": -0.1278, "formatted_address": "London, UK"},
    "manchester": {"latitude": 53.4808, "longitude": -2.2426, "formatted_address": "Manchester, UK"},
    "birmingham": {"latitude": 52.4862, "longitude": -1.8904, "formatted_address": "Birmingham, UK"},
    "leeds": {"latitude": 53.8008, "longitude": -1.5491, "formatted_address": "Leeds, UK"},
    "liverpool": {"latitude": 53.4084, "longitude": -2.9916, "formatted_address": "Liverpool, UK"},
    "bristol": {"latitude": 51.4545, "longitude": -2.5879, "formatted_address": "Bristol, UK"},
    "edinburgh": {"latitude": 55.9533, "longitude": -3.1883, "formatted_address": "Edinburgh, UK"},
    "glasgow": {"latitude": 55.8642, "longitude": -4.2518, "formatted_address": "Glasgow, UK"},
    "cardiff": {"latitude": 51.4816, "longitude": -3.1791, "formatted_address": "Cardiff, UK"},
    "sheffield": {"latitude": 53.3811, "longitude": -1.4701, "formatted_address": "Sheffield, UK"},
    "nottingham": {"latitude": 52.9548, "longitude": -1.1581, "formatted_address": "Nottingham, UK"},
    "newcastle": {"latitude": 54.9783, "longitude": -1.6178, "formatted_address": "Newcastle upon Tyne, UK"},
    "southampton": {"latitude": 50.9097, "longitude": -1.4044, "formatted_address": "Southampton, UK"},
    "portsmouth": {"latitude": 50.8198, "longitude": -1.0880, "formatted_address": "Portsmouth, UK"},
    "oxford": {"latitude": 51.7520, "longitude": -1.2577, "formatted_address": "Oxford, UK"},
    "cambridge": {"latitude": 52.2053, "longitude": 0.1218, "formatted_address": "Cambridge, UK"},
    "bath": {"latitude": 51.3811, "longitude": -2.3590, "formatted_address": "Bath, UK"},
    "york": {"latitude": 53.9591, "longitude": -1.0815, "formatted_address": "York, UK"},
    "reading": {"latitude": 51.4543, "longitude": -0.9781, "formatted_address": "Reading, UK"},
    "coventry": {"latitude": 52.4068, "longitude": -1.5197, "formatted_address": "Coventry, UK"},
    "leicester": {"latitude": 52.6369, "longitude": -1.1398, "formatted_address": "Leicester, UK"},
    "plymouth": {"latitude": 50.3755, "longitude": -4.1427, "formatted_address": "Plymouth, UK"},
    "exeter": {"latitude": 50.7184, "longitude": -3.5339, "formatted_address": "Exeter, UK"},
    "norwich": {"latitude": 52.6309, "longitude": 1.2974, "formatted_address": "Norwich, UK"},
    "derby": {"latitude": 52.9225, "longitude": -1.4746, "formatted_address": "Derby, UK"},
    "swansea": {"latitude": 51.6214, "longitude": -3.9436, "formatted_address": "Swansea, UK"},
    "chelmsford": {"latitude": 51.7356, "longitude": 0.4685, "formatted_address": "Chelmsford, UK"},
    "southminster": {"latitude": 51.6556, "longitude": 0.8424, "formatted_address": "Southminster, Essex, UK"},
    "lewes": {"latitude": 50.8730, "longitude": 0.0087, "formatted_address": "Lewes, East Sussex, UK"},
    "worthing": {"latitude": 50.8148, "longitude": -0.3721, "formatted_address": "Worthing, West Sussex, UK"},
    "eastbourne": {"latitude": 50.7684, "longitude": 0.2908, "formatted_address": "Eastbourne, East Sussex, UK"},
    "crawley": {"latitude": 51.1092, "longitude": -0.1872, "formatted_address": "Crawley, West Sussex, UK"},
    "sussex": {"latitude": 50.8825, "longitude": -0.2764, "formatted_address": "Sussex, UK"},
    "essex": {"latitude": 51.7343, "longitude": 0.4691, "formatted_address": "Essex, UK"},
    "chichester": {"latitude": 50.8376, "longitude": -0.7749, "formatted_address": "Chichester, West Sussex, UK"},
    "henfield": {"latitude": 50.9310, "longitude": -0.2760, "formatted_address": "Henfield, West Sussex, UK"},
    "steyning": {"latitude": 50.8869, "longitude": -0.3267, "formatted_address": "Steyning, West Sussex, UK"},
    "horsham": {"latitude": 51.0629, "longitude": -0.3277, "formatted_address": "Horsham, West Sussex, UK"},
    "hastings": {"latitude": 50.8543, "longitude": 0.5733, "formatted_address": "Hastings, East Sussex, UK"},
    "guildford": {"latitude": 51.2362, "longitude": -0.5704, "formatted_address": "Guildford, Surrey, UK"},
    "chester": {"latitude": 53.1910, "longitude": -2.8909, "formatted_address": "Chester, Cheshire, UK"},
    "lincoln": {"latitude": 53.2307, "longitude": -0.5406, "formatted_address": "Lincoln, Lincolnshire, UK"},
    "ipswich": {"latitude": 52.0567, "longitude": 1.1482, "formatted_address": "Ipswich, Suffolk, UK"},
    "colchester": {"latitude": 51.8959, "longitude": 0.8919, "formatted_address": "Colchester, Essex, UK"},
    "canterbury": {"latitude": 51.2802, "longitude": 1.0789, "formatted_address": "Canterbury, Kent, UK"},
    "dover": {"latitude": 51.1279, "longitude": 1.3134, "formatted_address": "Dover, Kent, UK"},
    "tunbridge wells": {"latitude": 51.1324, "longitude": 0.2637, "formatted_address": "Tunbridge Wells, Kent, UK"},
    "maidstone": {"latitude": 51.2720, "longitude": 0.5292, "formatted_address": "Maidstone, Kent, UK"},
}


def _lookup_cached(location: str) -> dict | None:
    """Check the fast UK locations cache (exact or pre-comma match only)."""
    key = location.lower().strip()
    if key in UK_LOCATIONS:
        return UK_LOCATIONS[key]
    head = key.split(",")[0].strip()
    if head and head in UK_LOCATIONS:
        return UK_LOCATIONS[head]
    return None


async def _nominatim_geocode(location: str) -> dict | None:
    """Geocode via OpenStreetMap Nominatim (free, no API key, UK-biased)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": location,
                "format": "json",
                "countrycodes": "gb",
                "limit": 1,
            },
            headers={"User-Agent": "Fliss-Caretopia/2.0"},
            timeout=10,
        )
        results = response.json()

    if not results:
        return None

    result = results[0]
    return {
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "formatted_address": result.get("display_name", location),
    }


async def geocode_location(location: str) -> dict | None:
    """Convert a location string to lat/lng.

    1. Check fast UK location cache
    2. Try Nominatim (free OpenStreetMap geocoding)
    3. Try Google Maps API if key available and unrestricted
    """
    # 1. Fast cache
    cached = _lookup_cached(location)
    if cached:
        return cached

    # 2. Nominatim (free, works server-side)
    try:
        result = await _nominatim_geocode(location)
        if result:
            return result
    except Exception:
        pass

    # 3. Google Maps fallback (only if key works server-side)
    settings = get_settings()
    if settings.use_live_geocoding:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={
                        "address": location,
                        "key": settings.google_maps_api_key,
                        "components": "country:GB",
                    },
                    timeout=10,
                )
                data = response.json()

            if data["status"] == "OK" and data["results"]:
                geo = data["results"][0]["geometry"]["location"]
                return {
                    "latitude": geo["lat"],
                    "longitude": geo["lng"],
                    "formatted_address": data["results"][0]["formatted_address"],
                }
        except Exception:
            pass

    return None
