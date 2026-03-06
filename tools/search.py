from __future__ import annotations
import asyncpg
from config import get_settings


_pool: asyncpg.Pool | None = None

# Map from our internal types to the DB enum values
TYPE_MAP = {
    "CAREHOME": "CAREHOME",
    "NURSERY": "NURSERY",
    "HOMECARE": "HOMECARE",
}


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(settings.database_url)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def search_listings(
    page_type: str,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float = 15.0,
    keywords: list[str] | None = None,
    limit: int = 8,
) -> list[dict]:
    """Search organisations in the real Caretopia Postgres database.

    Args:
        page_type: 'CAREHOME', 'NURSERY', or 'HOMECARE'.
        latitude: Latitude for geo search (from geocoding).
        longitude: Longitude for geo search (from geocoding).
        radius_km: Search radius in kilometres.
        keywords: Conditions/specialisms to filter by.
        limit: Max results (default 8).
    """
    settings = get_settings()
    if not settings.use_live_db:
        return _filter_test_data(page_type, keywords, limit)

    pool = await get_pool()
    db_type = TYPE_MAP.get(page_type, page_type)
    kw_list = keywords or []

    conditions = [
        "type = $1",
        '"isDeleted" = false',
        "status = 'ACTIVE'",
        "latitude IS NOT NULL",
        "longitude IS NOT NULL",
    ]
    params: list = [db_type]
    param_idx = 2

    # Haversine geo filter (earth radius = 6371 km)
    if latitude is not None and longitude is not None:
        conditions.append(f"""
            (6371 * acos(
                LEAST(GREATEST(
                    cos(radians(${param_idx})) * cos(radians(latitude))
                    * cos(radians(longitude) - radians(${param_idx + 1}))
                    + sin(radians(${param_idx})) * sin(radians(latitude))
                , -1), 1)
            )) <= ${param_idx + 2}
        """)
        params.extend([latitude, longitude, radius_km])
        param_idx += 3

    # Keyword filter — match against keywords JSON or description
    if kw_list:
        kw_conditions = []
        for kw in kw_list:
            kw_conditions.append(
                f"(keywords::text ILIKE ${param_idx} OR description ILIKE ${param_idx})"
            )
            params.append(f"%{kw}%")
            param_idx += 1
        conditions.append(f"({' OR '.join(kw_conditions)})")

    where_clause = " AND ".join(conditions)

    # Build distance calculation
    if latitude is not None and longitude is not None:
        distance_expr = f""",
            round((6371 * acos(
                LEAST(GREATEST(
                    cos(radians(${2})) * cos(radians(latitude))
                    * cos(radians(longitude) - radians(${3}))
                    + sin(radians(${2})) * sin(radians(latitude))
                , -1), 1)
            ))::numeric, 2) AS distance_km
        """
        order_clause = "ORDER BY distance_km ASC"
    else:
        distance_expr = ""
        order_clause = 'ORDER BY "createdAt" DESC'

    query = f"""
        SELECT
            o.id,
            o."organisationName",
            o."addressLine1",
            o."townCity",
            o.postcode,
            o.latitude,
            o.longitude,
            o.type,
            o.description,
            o.keywords,
            o."cqcGrade",
            o."ofstedGrade",
            o."overallRating",
            o."contactPhone",
            o."contactEmail",
            o.website,
            o."weeklyFeesGuide",
            o."facilitiesAndServices",
            o."registeredPlaces",
            o."fullAddress",
            o."managerName",
            o.slug,
            o."logoUrl",
            o."bannerUrl",
            o."minAge",
            o."maxAge",
            o.parking,
            o."companyStatus",
            o."inclusiveNursery",
            o."createdAt",
            o."socialMedia"
            {distance_expr}
        FROM organisations o
        WHERE {where_clause}
        {order_clause}
        LIMIT ${param_idx}
    """
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        results = []
        for row in rows:
            r = dict(row)
            # Convert Decimal latitude/longitude to float for JSON serialization
            if r.get("latitude") is not None:
                r["latitude"] = float(r["latitude"])
            if r.get("longitude") is not None:
                r["longitude"] = float(r["longitude"])
            if r.get("distance_km") is not None:
                r["distance_km"] = float(r["distance_km"])
            results.append(r)
        return results


# ── Test data fallback (no DB) ───────────────────────────────────────────────

TEST_CARE_HOMES = [
    {
        "id": 1, "organisationName": "Sunrise Manor Care Home", "type": "CAREHOME",
        "addressLine1": "14 Marine Parade", "townCity": "Brighton", "postcode": "BN2 1TL",
        "latitude": 50.8194, "longitude": -0.1235,
        "description": "A warm, family-run care home specialising in dementia and residential care.",
        "keywords": ["dementia", "residential", "respite"],
        "cqcGrade": "Good", "contactPhone": "01273 555 001",
    },
    {
        "id": 2, "organisationName": "The Willows Nursing Home", "type": "CAREHOME",
        "addressLine1": "8 Preston Road", "townCity": "Brighton", "postcode": "BN1 6AF",
        "latitude": 50.8411, "longitude": -0.1494,
        "description": "CQC Outstanding nursing home with specialist dementia unit.",
        "keywords": ["nursing", "dementia", "physiotherapy"],
        "cqcGrade": "Outstanding", "contactPhone": "01273 555 002",
    },
]

TEST_NURSERIES = [
    {
        "id": 101, "organisationName": "Little Stars Nursery", "type": "NURSERY",
        "addressLine1": "28 Church Road", "townCity": "Hove", "postcode": "BN3 2FN",
        "latitude": 50.8350, "longitude": -0.1720,
        "description": "Ofsted Outstanding nursery for ages 3 months to 5 years.",
        "keywords": ["forest school", "SEN support"],
        "ofstedGrade": "Outstanding", "contactPhone": "01273 555 101",
    },
]

TEST_HOME_CARE = [
    {
        "id": 201, "organisationName": "Compassionate Home Care", "type": "HOMECARE",
        "addressLine1": "Unit 3, Enterprise Point", "townCity": "Brighton", "postcode": "BN1 4GH",
        "latitude": 50.8380, "longitude": -0.1410,
        "description": "CQC Outstanding domiciliary care provider.",
        "keywords": ["personal care", "dementia", "live-in"],
        "cqcGrade": "Outstanding", "contactPhone": "01273 555 201",
    },
]

TEST_DATA = {
    "CAREHOME": TEST_CARE_HOMES,
    "NURSERY": TEST_NURSERIES,
    "HOMECARE": TEST_HOME_CARE,
}


def _filter_test_data(page_type: str, keywords: list[str] | None, limit: int) -> list[dict]:
    listings = TEST_DATA.get(page_type, [])
    if keywords:
        filtered = [
            l for l in listings
            if any(
                kw.lower() in (l.get("description", "") + " ".join(l.get("keywords", []))).lower()
                for kw in keywords
            )
        ]
        listings = filtered or listings
    results = []
    for i, listing in enumerate(listings[:limit]):
        results.append({**listing, "distance_km": round(1.2 + i * 1.8, 1)})
    return results
