from __future__ import annotations

from tools.aps_autocad.aps_client import APSClient


def main():

    client = APSClient()

    print("=" * 80)
    print("APS AUTOCAD CONNECTION TEST")
    print("=" * 80)

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    token = client.auth.get_token()

    print()
    print("OAuth: SUCCESS")
    print(
        "Token:",
        token[:12] + "...",
    )

    # ------------------------------------------------------------------
    # Configured engine
    # ------------------------------------------------------------------

    print()
    print("Configured engine:")
    print(client.engine)

    # ------------------------------------------------------------------
    # Query engines
    # ------------------------------------------------------------------

    print()
    print("Querying available engines...")

    response = client.request(
        "GET",
        "/da/us-east/v3/engines",
    )

    print()
    print("HTTP status:", response.status_code)

    response.raise_for_status()

    data = response.json()

    # APS returns an object containing the engine list.
    #
    # Depending on the API response/version, it may look like:
    #
    # {
    #     "data": [
    #         {
    #             "id": "Autodesk.AutoCAD+26_0",
    #             ...
    #         }
    #     ]
    # }
    #
    # or the response can be represented differently.
    #
    # Handle both safely.

    if isinstance(data, dict):

        if isinstance(data.get("data"), list):
            engines = data["data"]

        elif isinstance(data.get("engines"), list):
            engines = data["engines"]

        else:
            print()
            print("Unexpected APS engine response:")
            print(data)

            engines = []

    elif isinstance(data, list):

        engines = data

    else:

        print()
        print("Unexpected APS response type:")
        print(type(data))

        engines = []

    # ------------------------------------------------------------------
    # Normalize engine records
    # ------------------------------------------------------------------

    normalized_engines = []

    for engine in engines:

        if isinstance(engine, dict):

            normalized_engines.append(engine)

        elif isinstance(engine, str):

            # Some APS responses may expose IDs directly.
            normalized_engines.append(
                {
                    "id": engine
                }
            )

    # ------------------------------------------------------------------
    # Find configured engine
    # ------------------------------------------------------------------

    found = [
        engine
        for engine in normalized_engines
        if engine.get("id") == client.engine
    ]

    if found:

        print()
        print("=" * 80)
        print("AUTOCAD ENGINE FOUND")
        print("=" * 80)

        engine = found[0]

        for key, value in engine.items():
            print(f"{key}: {value}")

    else:

        print()
        print("=" * 80)
        print("CONFIGURED AUTOCAD ENGINE NOT FOUND")
        print("=" * 80)

        print()
        print("Configured:")
        print(
            client.engine
        )

        print()
        print("Available AutoCAD engines:")

        autocad_engines = []

        for engine in normalized_engines:

            engine_id = str(
                engine.get(
                    "id",
                    "",
                )
            )

            if "AutoCAD" in engine_id:

                autocad_engines.append(
                    engine_id
                )

        if autocad_engines:

            for engine_id in autocad_engines:
                print(
                    " -",
                    engine_id,
                )

        else:

            print(
                "No AutoCAD engines returned."
            )

    # ------------------------------------------------------------------
    # Diagnostic response
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("APS ENGINE TEST COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Total engine records: "
        f"{len(normalized_engines)}"
    )


if __name__ == "__main__":
    main()
