import requests

CATFACT_URL = "https://catfact.ninja/fact"

def get_cat_fact() -> str:
    resp = requests.get(CATFACT_URL, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return data.get("fact", "")
