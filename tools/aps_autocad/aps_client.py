from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


APS_BASE_URL = "https://developer.api.autodesk.com"

DA_BASE_URL = (
    f"{APS_BASE_URL}/da/us-east/v3"
)

AUTH_URL = (
    f"{APS_BASE_URL}/authentication/v2/token"
)


class APSAuth:
    """
    APS OAuth 2-legged client.
    """

    def __init__(self):
        self.client_id = os.getenv("APS_CLIENT_ID")
        self.client_secret = os.getenv("APS_CLIENT_SECRET")

        if not self.client_id:
            raise RuntimeError(
                "APS_CLIENT_ID is not configured"
            )

        if not self.client_secret:
            raise RuntimeError(
                "APS_CLIENT_SECRET is not configured"
            )

    def get_token(
        self,
        scopes: str | None = None,
    ) -> str:

        if scopes is None:
            scopes = (
                "code:all "
                "bucket:create "
                "bucket:read "
                "data:read "
                "data:write"
            )

        response = requests.post(
            AUTH_URL,
            auth=(
                self.client_id,
                self.client_secret,
            ),
            data={
                "grant_type": "client_credentials",
                "scope": scopes,
            },
            headers={
                "Content-Type":
                    "application/x-www-form-urlencoded",
                "Accept":
                    "application/json",
            },
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                "APS OAuth failed\n"
                f"HTTP: {response.status_code}\n"
                f"{response.text}"
            )

        data = response.json()

        token = data.get("access_token")

        if not token:
            raise RuntimeError(
                "APS did not return an access token"
            )

        return token


class APSClient:
    """
    Small REST client for APS Automation and OSS.
    """

    def __init__(self):

        self.auth = APSAuth()

        self.client_id = (
            self.auth.client_id
        )

        self.engine = os.getenv(
            "APS_ENGINE",
            "Autodesk.AutoCAD+26_0",
        )

    def token(self) -> str:

        return self.auth.get_token()

    def headers(
        self,
        token: str | None = None,
    ) -> dict[str, str]:

        if token is None:
            token = self.token()

        return {
            "Authorization":
                f"Bearer {token}",
            "Accept":
                "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:

        if path.startswith("http"):
            url = path
        else:
            url = (
                APS_BASE_URL + path
            )

        token = kwargs.pop(
            "token",
            None,
        )

        headers = kwargs.pop(
            "headers",
            {},
        )

        merged_headers = self.headers(
            token
        )

        merged_headers.update(
            headers
        )

        response = requests.request(
            method,
            url,
            headers=merged_headers,
            timeout=120,
            **kwargs,
        )

        return response
