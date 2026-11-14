#!/usr/bin/env python3
"""List Buffer organizations and channels using BUFFER_ACCESS_TOKEN.

Does not print the token. Redacts account email. Run this once during setup
so Publisher and Analyst can map channel names to ids in a private config,
not in this public repo.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request


def gql(token: str, query: str, variables=None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.buffer.com",
        data=body,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def main() -> None:
    token = os.environ.get("BUFFER_ACCESS_TOKEN") or ""
    if not token:
        print("Missing BUFFER_ACCESS_TOKEN in the environment.", file=sys.stderr)
        sys.exit(2)
    data = gql(token, "query{account{id organizations{id name channelCount limits{channels}}}}")
    orgs = ((data.get("data") or {}).get("account") or {}).get("organizations") or []
    out = {"organizations": []}
    for org in orgs:
        channels = gql(
            token,
            "query($i:OrganizationId!){channels(input:{organizationId:$i}){id name displayName service type isDisconnected isLocked}}",
            {"i": org["id"]},
        )
        out["organizations"].append(
            {
                "id": org.get("id"),
                "name": org.get("name"),
                "channelCount": org.get("channelCount"),
                "channels": (channels.get("data") or {}).get("channels") or [],
            }
        )
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
