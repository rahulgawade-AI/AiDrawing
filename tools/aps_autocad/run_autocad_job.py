from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import quote

import requests

from tools.aps_autocad.aps_client import APSClient, APS_BASE_URL


# ============================================================
# CONFIGURATION
# ============================================================

ACTIVITY_NAME = "TownPlanningAutoCADTestV7"
ACTIVITY_ALIAS = "prod"


# ============================================================
# HELPERS
# ============================================================

def print_json(title: str, data):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)
    print(json.dumps(data, indent=2))


# ============================================================
# OSS BUCKET
# ============================================================

def ensure_bucket(
    token: str,
    bucket_key: str,
):
    url = f"{APS_BASE_URL}/oss/v2/buckets"

    payload = {
        "bucketKey": bucket_key,
        "access": "full",
        "policyKey": "transient",
    }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    if response.status_code in (200, 201):
        print("OSS bucket created.")
        return

    if response.status_code == 409:
        print("OSS bucket already exists.")
        return

    raise RuntimeError(
        "Could not create/check OSS bucket\n"
        f"HTTP: {response.status_code}\n"
        f"{response.text}"
    )


# ============================================================
# SIGNED UPLOAD URL
# ============================================================

def create_signed_upload_url(
    token: str,
    bucket_key: str,
    object_key: str,
):
    encoded_key = quote(
        object_key,
        safe="",
    )

    url = (
        f"{APS_BASE_URL}/oss/v2/"
        f"buckets/{bucket_key}/objects/"
        f"{encoded_key}/signeds3upload"
        f"?minutesExpiration=30"
    )

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            "Could not create S3 upload URL\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text}"
        )

    return response.json()


# ============================================================
# UPLOAD INPUT DXF
# ============================================================

def upload_file_to_oss(
    token: str,
    bucket_key: str,
    object_key: str,
    file_path: Path,
):
    print()
    print("Uploading input DXF:")
    print(file_path)

    signed = create_signed_upload_url(
        token,
        bucket_key,
        object_key,
    )

    urls = signed.get("urls", [])

    if not urls:
        raise RuntimeError(
            "APS did not return signed upload URL."
        )

    with open(file_path, "rb") as file:
        response = requests.put(
            urls[0],
            data=file,
            headers={
                "Content-Type":
                    "application/octet-stream"
            },
            timeout=300,
        )

    if not response.ok:
        raise RuntimeError(
            "S3 upload failed\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text}"
        )

    upload_key = signed.get("uploadKey")

    if not upload_key:
        raise RuntimeError(
            "APS did not return uploadKey."
        )

    finalize_url = (
        f"{APS_BASE_URL}/oss/v2/"
        f"buckets/{bucket_key}/objects/"
        f"{quote(object_key, safe='')}/"
        f"signeds3upload"
    )

    finalize_payload = {
        "ossbucketKey": bucket_key,
        "ossSourceFileObjectKey": object_key,
        "access": "full",
        "uploadKey": upload_key,
    }

    response = requests.post(
        finalize_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=finalize_payload,
        timeout=120,
    )

    if not response.ok:
        raise RuntimeError(
            "OSS upload finalization failed\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text}"
        )

    print("Input DXF uploaded successfully.")

    return response.json()


# ============================================================
# SIGNED OBJECT URL
# ============================================================

def create_signed_object_url(
    token: str,
    bucket_key: str,
    object_key: str,
    access: str,
):
    encoded_key = quote(
        object_key,
        safe="",
    )

    url = (
        f"{APS_BASE_URL}/oss/v2/"
        f"buckets/{bucket_key}/objects/"
        f"{encoded_key}/signed"
        f"?access={access}"
        f"&useCdn=true"
    )

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "minutesExpiration": 60,
            "singleUse": False,
        },
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            "Could not create signed object URL\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text}"
        )

    data = response.json()

    signed_url = data.get("signedUrl")

    if not signed_url:
        raise RuntimeError(
            "APS response did not contain signedUrl."
        )

    return signed_url


# ============================================================
# CREATE ACTIVITY
# ============================================================

def create_activity(
    client: APSClient,
    token: str,
):
    print()
    print("Creating APS Activity:")
    print(
        f"{client.client_id}."
        f"{ACTIVITY_NAME}"
    )

    # IMPORTANT:
    #
    # AutoCAD Core Console opened the DXF correctly in V3.
    #
    # V3 failed because QSAVE hung.
    #
    # Earlier SAVEAS failed because the parameters were:
    #
    #     SAVEAS
    #     2018
    #     result.dwg
    #
    # AutoCAD interpreted "result.dwg" as the FILE FORMAT.
    #
    # Correct order:
    #
    #     SAVEAS
    #     result.dwg
    #     2018
    #
    # Therefore we explicitly use:
    #
    #     _.SAVEAS
    #     result.dwg
    #     2018
    #
    # The final blank line handles any confirmation prompt.

    activity = {

        "id":
            ACTIVITY_NAME,

        "engine":
            client.engine,

        "description":
            "Town planning DXF to DWG "
            "conversion using AutoCAD Core Console",

        "appbundles":
            [],

        "commandLine": [

            '$(engine.path)\\accoreconsole.exe '
            '/i "$(args[HostDwg].path)" '
            '/s "$(settings[script].path)" '
            '/suppressGraphics'
        ],

        "parameters": {

            "HostDwg": {

                "verb":
                    "get",

                "description":
                    "Town planning DXF input",

                "required":
                    True,

                "localName":
                    "input.dxf",
            },

            "Result": {

                "verb":
                    "put",

                "description":
                    "Generated AutoCAD DWG",

                "required":
                    True,

                "localName":
                    "result.dwg",
            },
        },

        "settings": {

            "script": {

                "value":
                    "_.FILEDIA\n"
                    "0\n"
                    "_.CMDECHO\n"
                    "0\n"
                    "_.SAVEAS\n"
                    "\n"
                    "result.dwg\n"
            }
        },
    }

    print_json(
        "ACTIVITY REQUEST",
        activity,
    )

    response = client.request(
        "POST",
        "/da/us-east/v3/activities",
        token=token,
        json=activity,
        headers={
            "Content-Type":
                "application/json",
        },
    )

    if not response.ok:
        raise RuntimeError(
            "Activity creation failed\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text}"
        )

    result = response.json()

    print_json(
        "ACTIVITY CREATED",
        result,
    )

    version = result.get(
        "version",
        1,
    )

    # --------------------------------------------------------
    # Create alias
    # --------------------------------------------------------

    response = client.request(
        "POST",
        f"/da/us-east/v3/activities/"
        f"{ACTIVITY_NAME}/aliases",
        token=token,
        json={
            "id":
                ACTIVITY_ALIAS,

            "version":
                version,
        },
        headers={
            "Content-Type":
                "application/json",
        },
    )

    if not response.ok:

        # If alias already exists, don't fail the test.
        if response.status_code == 409:

            print()
            print(
                "Activity alias already exists."
            )

        else:

            raise RuntimeError(
                "Activity alias creation failed\n"
                f"HTTP: {response.status_code}\n"
                f"{response.text}"
            )

    print()
    print("Activity alias:")
    print(
        f"{client.client_id}."
        f"{ACTIVITY_NAME}+"
        f"{ACTIVITY_ALIAS}"
    )


# ============================================================
# CREATE WORK ITEM
# ============================================================

def create_workitem(
    client: APSClient,
    token: str,
    input_url: str,
    output_url: str,
):
    activity_id = (
        f"{client.client_id}."
        f"{ACTIVITY_NAME}+"
        f"{ACTIVITY_ALIAS}"
    )

    payload = {

        "activityId":
            activity_id,

        "arguments": {

            "HostDwg": {

                "url":
                    input_url,

                "verb":
                    "get",

                "localName":
                    "input.dxf",
            },

            "Result": {

                "url":
                    output_url,

                "verb":
                    "put",

                "localName":
                    "result.dwg",
            },
        },

        "limitProcessingTimeSec":
            900,
    }

    print()
    print("Submitting APS WorkItem...")

    response = client.request(
        "POST",
        "/da/us-east/v3/workitems",
        token=token,
        json=payload,
        headers={
            "Content-Type":
                "application/json",
        },
    )

    if not response.ok:
        raise RuntimeError(
            "WorkItem creation failed\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text}"
        )

    result = response.json()

    print_json(
        "WORKITEM CREATED",
        result,
    )

    return result


# ============================================================
# GET WORK ITEM
# ============================================================

def get_workitem(
    client: APSClient,
    token: str,
    workitem_id: str,
):
    response = client.request(
        "GET",
        f"/da/us-east/v3/workitems/"
        f"{workitem_id}",
        token=token,
    )

    if not response.ok:
        raise RuntimeError(
            "Could not get WorkItem status\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text}"
        )

    return response.json()


# ============================================================
# DOWNLOAD FILE
# ============================================================

def download_file(
    url: str,
    destination: Path,
):
    response = requests.get(
        url,
        timeout=300,
    )

    if not response.ok:
        raise RuntimeError(
            "DWG download failed\n"
            f"HTTP: {response.status_code}\n"
            f"{response.text}"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(
        response.content
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Convert a town-planning DXF "
            "to DWG using APS AutoCAD."
        )
    )

    parser.add_argument(
        "--input",
        default=(
            "/tmp/building_plan/"
            "B01_floor_01.dxf"
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "/tmp/aps_autocad_output"
        ),
    )

    args = parser.parse_args()

    input_file = Path(
        args.input
    ).resolve()

    output_dir = Path(
        args.output_dir
    ).resolve()

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not input_file.exists():

        raise FileNotFoundError(
            "Input DXF does not exist:\n"
            f"{input_file}"
        )

    output_file = (
        output_dir /
        f"{input_file.stem}_aps.dwg"
    )

    print("=" * 80)
    print("APS AUTOCAD DXF → DWG TEST")
    print("=" * 80)

    print()
    print("INPUT DXF:")
    print(input_file)

    print()
    print("OUTPUT DWG:")
    print(output_file)

    client = APSClient()

    print()
    print("ENGINE:")
    print(client.engine)

    # --------------------------------------------------------
    # OAuth
    # --------------------------------------------------------

    token = client.token()

    print()
    print("OAuth: SUCCESS")

    # --------------------------------------------------------
    # Temporary OSS bucket
    # --------------------------------------------------------

    bucket_key = (
        "townplanning_"
        + client.client_id.lower()
        + "_v4"
    )

    bucket_key = "".join(
        character
        for character in bucket_key
        if character.isalnum()
        or character == "_"
    )

    bucket_key = bucket_key[:100]

    print()
    print("OSS BUCKET:")
    print(bucket_key)

    ensure_bucket(
        token,
        bucket_key,
    )

    # --------------------------------------------------------
    # Object names
    # --------------------------------------------------------

    timestamp = int(
        time.time()
    )

    input_object = (
        f"v4_{timestamp}_"
        f"{input_file.name}"
    )

    output_object = (
        f"v4_{timestamp}_"
        f"{input_file.stem}.dwg"
    )

    # --------------------------------------------------------
    # Upload DXF
    # --------------------------------------------------------

    upload_file_to_oss(
        token,
        bucket_key,
        input_object,
        input_file,
    )

    # --------------------------------------------------------
    # Signed input URL
    # --------------------------------------------------------

    input_url = create_signed_object_url(
        token,
        bucket_key,
        input_object,
        "read",
    )

    # --------------------------------------------------------
    # Signed output URL
    # --------------------------------------------------------

    output_url = create_signed_object_url(
        token,
        bucket_key,
        output_object,
        "readwrite",
    )

    # --------------------------------------------------------
    # Create Activity
    # --------------------------------------------------------

    create_activity(
        client,
        token,
    )

    # --------------------------------------------------------
    # Create WorkItem
    # --------------------------------------------------------

    workitem = create_workitem(
        client,
        token,
        input_url,
        output_url,
    )

    workitem_id = workitem["id"]

    print()
    print("Monitoring WorkItem:")
    print(workitem_id)

    terminal_statuses = {
        "success",
        "failed",
        "failedInstructions",
        "failedDownload",
        "failedUpload",
        "cancelled",
        "timedOut",
    }

    final_status = None

    # --------------------------------------------------------
    # Poll WorkItem
    # --------------------------------------------------------

    for attempt in range(
        1,
        181,
    ):

        status = get_workitem(
            client,
            token,
            workitem_id,
        )

        state = status.get(
            "status"
        )

        print(
            f"[{attempt:03d}] "
            f"status={state}"
        )

        if state in terminal_statuses:

            final_status = status

            break

        time.sleep(5)

    if final_status is None:

        raise RuntimeError(
            "APS WorkItem monitoring timeout."
        )

    print_json(
        "FINAL WORKITEM STATUS",
        final_status,
    )

    # --------------------------------------------------------
    # Download APS report
    # --------------------------------------------------------

    report_url = final_status.get(
        "reportUrl"
    )

    if report_url:

        report_response = requests.get(
            report_url,
            timeout=120,
        )

        report_path = (
            output_dir /
            f"{input_file.stem}_"
            "aps_report.txt"
        )

        if report_response.ok:

            report_path.write_text(
                report_response.text,
                encoding="utf-8",
            )

            print()
            print("Report saved:")
            print(report_path)

        else:

            print()
            print(
                "WARNING: Could not "
                "download APS report."
            )

    # --------------------------------------------------------
    # Failed
    # --------------------------------------------------------

    if final_status.get(
        "status"
    ) != "success":

        print()
        print("=" * 80)
        print("APS AUTOCAD JOB FAILED")
        print("=" * 80)

        print()
        print(
            "WorkItem:",
            workitem_id,
        )

        print(
            "Status:",
            final_status.get(
                "status"
            ),
        )

        raise RuntimeError(
            "APS AutoCAD WorkItem failed."
        )

    # --------------------------------------------------------
    # Download generated DWG
    # --------------------------------------------------------

    print()
    print("APS WorkItem successful.")
    print("Downloading generated DWG...")

    result_url = create_signed_object_url(
        token,
        bucket_key,
        output_object,
        "read",
    )

    download_file(
        result_url,
        output_file,
    )

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    if not output_file.exists():

        raise RuntimeError(
            "APS reported success but "
            "DWG file does not exist."
        )

    size = output_file.stat().st_size

    if size == 0:

        raise RuntimeError(
            "APS returned an empty DWG."
        )

    print()
    print("=" * 80)
    print("APS AUTOCAD JOB SUCCESSFUL")
    print("=" * 80)

    print()
    print("Generated DWG:")
    print(output_file)

    print()
    print(
        "DWG size:",
        size,
        "bytes",
    )

    print()
    print("NEXT STEP:")
    print(
        "Open the generated DWG in AutoCAD "
        "and verify the floor-plan geometry."
    )


if __name__ == "__main__":
    main()
