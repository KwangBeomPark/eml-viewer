from __future__ import annotations

import json
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eml_viewer.services.update_service import UpdateCheckError, UpdateService


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class UpdateServiceTest(unittest.TestCase):
    def test_update_available_uses_installer_asset(self) -> None:
        payload = {
            "tag_name": "v0.2.0",
            "html_url": "https://github.com/KwangBeomPark/eml-viewer/releases/tag/v0.2.0",
            "assets": [
                {
                    "name": "EmlViewerSetup-0.2.0.exe",
                    "browser_download_url": "https://example.com/EmlViewerSetup-0.2.0.exe",
                }
            ],
        }

        service = UpdateService(current_version="0.1.0", opener=lambda request, timeout: FakeResponse(payload))
        result = service.check_for_updates()

        self.assertTrue(result.update_available)
        self.assertEqual(result.latest_version, "0.2.0")
        self.assertEqual(result.download_url, "https://example.com/EmlViewerSetup-0.2.0.exe")

    def test_same_version_is_latest(self) -> None:
        payload = {
            "tag_name": "v0.1.0",
            "html_url": "https://github.com/KwangBeomPark/eml-viewer/releases/tag/v0.1.0",
            "assets": [],
        }

        service = UpdateService(current_version="0.1.0", opener=lambda request, timeout: FakeResponse(payload))
        result = service.check_for_updates()

        self.assertFalse(result.update_available)

    def test_network_error_becomes_user_level_error(self) -> None:
        def failing_opener(request, timeout):
            raise urllib.error.URLError("offline")

        service = UpdateService(current_version="0.1.0", opener=failing_opener)

        with self.assertRaises(UpdateCheckError):
            service.check_for_updates()

    def test_missing_latest_release_has_actionable_message(self) -> None:
        def failing_opener(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

        service = UpdateService(current_version="0.1.0", opener=failing_opener)

        with self.assertRaises(UpdateCheckError) as context:
            service.check_for_updates()

        self.assertIn("배포 정보를 찾을 수 없습니다", str(context.exception))

    def test_unexpected_payload_shape_becomes_user_level_error(self) -> None:
        service = UpdateService(current_version="0.1.0", opener=lambda request, timeout: FakeResponse([]))

        with self.assertRaises(UpdateCheckError):
            service.check_for_updates()


if __name__ == "__main__":
    unittest.main()
