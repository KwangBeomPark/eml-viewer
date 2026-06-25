from __future__ import annotations

import io
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eml_viewer.services.update_service import (
    OperationCanceled,
    UpdateDownloadError,
    UpdateService,
)


class FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._stream = io.BytesIO(data)
        self.headers = {"content-length": str(len(data))}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self, block_size: int = 8192) -> bytes:
        return self._stream.read(block_size)


class UpdateDownloadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dest_path = os.path.join(self.temp_dir.name, "installer.exe")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_successful_download(self) -> None:
        data = b"a" * 20000
        progress_calls = []

        def progress_cb(downloaded: int, total: int) -> None:
            progress_calls.append((downloaded, total))

        def fake_opener(request, timeout):
            return FakeResponse(data)

        service = UpdateService(opener=fake_opener)
        service.download_installer(
            url="https://example.com/setup.exe",
            dest_path=self.dest_path,
            progress_callback=progress_cb,
        )

        self.assertTrue(os.path.exists(self.dest_path))
        with open(self.dest_path, "rb") as f:
            self.assertEqual(f.read(), data)

        # Check progress calls
        self.assertTrue(len(progress_calls) > 0)
        self.assertEqual(progress_calls[-1], (20000, 20000))

    def test_cancellation(self) -> None:
        data = b"b" * 20000
        cancel_event = threading.Event()

        # We cancel the download on the first progress callback
        def progress_cb(downloaded: int, total: int) -> None:
            cancel_event.set()

        def fake_opener(request, timeout):
            return FakeResponse(data)

        service = UpdateService(opener=fake_opener)

        with self.assertRaises(OperationCanceled):
            service.download_installer(
                url="https://example.com/setup.exe",
                dest_path=self.dest_path,
                progress_callback=progress_cb,
                cancel_event=cancel_event,
            )

        # Temp file should be deleted on cancellation
        self.assertFalse(os.path.exists(self.dest_path))

    def test_download_error_cleanup(self) -> None:
        def fake_opener(request, timeout):
            raise ValueError("connection error")

        service = UpdateService(opener=fake_opener)

        with self.assertRaises(UpdateDownloadError):
            service.download_installer(
                url="https://example.com/setup.exe",
                dest_path=self.dest_path,
            )

        self.assertFalse(os.path.exists(self.dest_path))

    def test_download_error_preserves_existing_destination(self) -> None:
        existing_data = b"existing installer"
        with open(self.dest_path, "wb") as f:
            f.write(existing_data)

        def fake_opener(request, timeout):
            raise ValueError("connection error")

        service = UpdateService(opener=fake_opener)

        with self.assertRaises(UpdateDownloadError):
            service.download_installer(
                url="https://example.com/setup.exe",
                dest_path=self.dest_path,
            )

        self.assertTrue(os.path.exists(self.dest_path))
        with open(self.dest_path, "rb") as f:
            self.assertEqual(f.read(), existing_data)

    def test_empty_download_is_rejected(self) -> None:
        def fake_opener(request, timeout):
            return FakeResponse(b"")

        service = UpdateService(opener=fake_opener)

        with self.assertRaises(UpdateDownloadError):
            service.download_installer(
                url="https://example.com/setup.exe",
                dest_path=self.dest_path,
            )

        self.assertFalse(os.path.exists(self.dest_path))


if __name__ == "__main__":
    unittest.main()
