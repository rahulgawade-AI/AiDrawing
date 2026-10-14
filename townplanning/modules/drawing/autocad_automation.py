from __future__ import annotations
import json
from pathlib import Path

class AutoCADAutomationClient:
    """Adapter boundary for Autodesk Platform Services AutoCAD Automation.

    APS credentials, app bundle/activity IDs, and HTTP submission belong here.
    The drawing optimizer remains independent of Autodesk.
    """
    def __init__(self, activity_id=None, app_bundle=None):
        self.activity_id = activity_id
        self.app_bundle = app_bundle

    def build_job_payload(self, cad_payload):
        if not self.activity_id:
            raise ValueError("Configure the Autodesk Automation activity_id.")
        return {
            "activity_id": self.activity_id,
            "app_bundle": self.app_bundle,
            "parameters": {
                "design_specification": json.dumps(
                    cad_payload, ensure_ascii=False, default=str
                )
            },
        }

    def write_job_payload(self, cad_payload, output_path):
        path = Path(output_path)
        path.write_text(
            json.dumps(self.build_job_payload(cad_payload), indent=2, default=str),
            encoding="utf-8",
        )
        return path
