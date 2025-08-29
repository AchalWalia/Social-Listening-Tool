from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import requests

from app.config import ABSTRACT_API_KEY, THECOMPANIESAPI_KEY


@dataclass
class CompanyCandidate:
    name: str
    domain: Optional[str]


def _query_thecompaniesapi(query: str) -> List[CompanyCandidate]:
    if not THECOMPANIESAPI_KEY:
        return []
    try:
        resp = requests.get(
            "https://api.thecompaniesapi.com/v1/companies/search",
            params={"q": query, "limit": 5},
            headers={"x-api-key": THECOMPANIESAPI_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", [])
        return [CompanyCandidate(name=r.get("name"), domain=r.get("domain")) for r in results]
    except Exception:
        return []


def _query_abstract(query: str) -> List[CompanyCandidate]:
    if not ABSTRACT_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://companyenrichment.abstractapi.com/v1/companies/autocomplete",
            params={"api_key": ABSTRACT_API_KEY, "query": query, "limit": 5},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [CompanyCandidate(name=r.get("name"), domain=r.get("domain")) for r in data]
    except Exception:
        return []


def _query_clearbit(query: str) -> List[CompanyCandidate]:
    try:
        resp = requests.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": query},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [CompanyCandidate(name=r.get("name"), domain=r.get("domain")) for r in data[:5]]
    except Exception:
        return []


def validate_company(query: str) -> List[CompanyCandidate]:
    # Try providers in order, then free fallback
    results = _query_thecompaniesapi(query)
    if results:
        return results
    results = _query_abstract(query)
    if results:
        return results
    results = _query_clearbit(query)
    if results:
        return results
    # Fallback: return raw query as a single candidate without domain
    return [CompanyCandidate(name=query, domain=None)] 