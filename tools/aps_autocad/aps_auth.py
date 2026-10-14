from __future__ import annotations

import os
import time
import requests

from dotenv import load_dotenv


load_dotenv()


class APSAuth:

    TOKEN_URL = (
        "https://developer.api.autodesk.com"
        "/authentication/v2/token"
    )

    def __init__(self):
        self.client_id = os.environ["APS_CLIENT_ID"]
        self.client_secret = os.environ["APS_CLIENT_SECRET"]

        self.token = None
        self.expires_at = 0

    def get_token(self):

        if (
            self.token
            and time.time() < self.expires_at - 60
        ):
            return self.token

        response = requests.post(
            self.TOKEN_URL,
            auth=(
                self.client_id,
                self.client_secret,
            ),
            data={
                "grant_type": "client_credentials",
                "scope": "code:all",
            },
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "APS authentication failed:\n"
                f"HTTP {response.status_code}\n"
                f"{response.text}"
            )

        data = response.json()

        self.token = data["access_token"]

        self.expires_at = (
            time.time()
            + int(data["expires_in"])
        )

        return self.token
