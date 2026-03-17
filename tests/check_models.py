"""Check for new Winix models or attributes not in our known snapshot.

Fetches the current model list from the Winix API and compares against
tests/known_models.json. Fails if new models or unknown attributes are found.

Usage:
    WINIX_USERNAME=email WINIX_PASSWORD=pass python tests/check_models.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import aiohttp

from custom_components.winix_purifiers.api.account import WinixAccount
from custom_components.winix_purifiers.api.auth import WinixAuth
from custom_components.winix_purifiers.api.const import (
    COGNITO_CLIENT_SECRET_KEY,
    MOBILE_APP_VERSION,
    MOBILE_LANG,
    MOBILE_MODEL,
    MOBILE_OS_TYPE,
    MOBILE_OS_VERSION,
)
from custom_components.winix_purifiers.api.crypto import decrypt, encrypt

KNOWN_ATTRS = {
    "A02",
    "A03",
    "A04",
    "A05",
    "A07",
    "A08",
    "A09",
    "A10",
    "A11",
    "A12",
    "A15",
    "A16",
    "A21",
}

KNOWN_MODELS_PATH = Path(__file__).parent / "known_models.json"


async def fetch_model_list(session: aiohttp.ClientSession, access_token: str, uuid: str) -> dict:
    """Fetch the full model list from the Winix API."""
    payload = {
        "cognitoClientSecretKey": COGNITO_CLIENT_SECRET_KEY,
        "accessToken": access_token,
        "uuid": uuid,
        "osType": MOBILE_OS_TYPE,
        "osVersion": MOBILE_OS_VERSION,
        "mobileLang": MOBILE_LANG,
        "appVersion": MOBILE_APP_VERSION,
        "mobileModel": MOBILE_MODEL,
    }

    encrypted = encrypt(payload)
    async with session.post(
        "https://us.mobile.winix-iot.com/getAllModelGroupInfoList",
        data=encrypted,
        headers={
            "Content-Type": "application/octet-stream",
            "Accept": "application/octet-stream",
        },
    ) as resp:
        data = await resp.read()

    return decrypt(data)


async def main() -> None:
    username = os.environ.get("WINIX_USERNAME")
    password = os.environ.get("WINIX_PASSWORD")

    if not username or not password:
        print("Set WINIX_USERNAME and WINIX_PASSWORD")
        sys.exit(1)

    auth = WinixAuth.login(username, password)

    async with aiohttp.ClientSession() as session:
        account = await WinixAccount._create(session, username, auth)
        response = await fetch_model_list(session, account.auth.access_token, account._uuid)

    # Build current model -> attrs mapping (air purifiers only)
    current: dict[str, list[str]] = {}
    for group in response.get("modelGroupInfoList", []):
        for model in group.get("modelInfoList", []):
            pg = model.get("productGroup", "")
            if not pg.startswith("Air"):
                continue
            name = model["modelName"]
            attrs = sorted(c["attrId"] for c in model.get("controlInfoList", []))
            if name not in current:
                current[name] = attrs

    current = dict(sorted(current.items()))

    # Load known snapshot
    known: dict[str, list[str]] = {}
    if KNOWN_MODELS_PATH.exists():
        known = json.loads(KNOWN_MODELS_PATH.read_text())

    # Compare
    issues: list[str] = []

    new_models = set(current) - set(known)
    if new_models:
        for model in sorted(new_models):
            issues.append(f"NEW MODEL: {model} with attrs {current[model]}")

    removed_models = set(known) - set(current)
    if removed_models:
        for model in sorted(removed_models):
            issues.append(f"REMOVED MODEL: {model}")

    for model in sorted(set(current) & set(known)):
        current_attrs = set(current[model])
        known_attrs = set(known[model])
        new_attrs = current_attrs - known_attrs
        removed_attrs = known_attrs - current_attrs
        if new_attrs:
            issues.append(f"NEW ATTRS for {model}: {sorted(new_attrs)}")
        if removed_attrs:
            issues.append(f"REMOVED ATTRS for {model}: {sorted(removed_attrs)}")

    # Check for completely unknown attribute codes
    all_current_attrs: set[str] = set()
    for attrs in current.values():
        all_current_attrs.update(attrs)
    unknown_attrs = all_current_attrs - KNOWN_ATTRS
    if unknown_attrs:
        issues.append(f"UNKNOWN ATTRIBUTE CODES: {sorted(unknown_attrs)}")

    if issues:
        print("Model changes detected:\n")
        for issue in issues:
            print(f"  {issue}")
        print("\nUpdate tests/known_models.json if these are expected.")
        sys.exit(1)
    else:
        print(f"No changes detected. {len(current)} models checked.")


if __name__ == "__main__":
    asyncio.run(main())
