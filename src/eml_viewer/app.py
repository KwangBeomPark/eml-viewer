from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

from eml_viewer import __version__


def _show_unhandled_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error(
        "Unhandled exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        if app is None:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        QMessageBox.critical(
            None,
            "예상하지 못한 오류",
            "프로그램에서 예상하지 못한 오류가 발생했습니다.\n\n"
            "가능하면 작업을 다시 시도해 주세요.\n\n"
            f"상세 정보:\n{details}",
        )
    except Exception:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


def _resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_path / relative_path


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    sys.excepthook = _show_unhandled_exception

    # Windows 전용 네임드 뮤텍스 생성 (인스톨러에서 실행 중인 프로세스 감지용)
    mutex_handle = None
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            CreateMutex = ctypes.windll.kernel32.CreateMutexW
            CreateMutex.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            CreateMutex.restype = wintypes.HANDLE
            mutex_handle = CreateMutex(None, False, "EmlViewerMutex")
        except Exception as exc:
            logging.warning(f"네임드 뮤텍스 생성 실패: {exc}")

    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError:
        print(
            "PySide6가 설치되어 있지 않습니다. "
            "'python -m pip install -e .' 명령으로 필요한 패키지를 설치해 주세요.",
            file=sys.stderr,
        )
        return 1

    from eml_viewer.gui.main_window import MainWindow
    from eml_viewer.services.attachment_service import AttachmentService
    from eml_viewer.services.eml_parser import EmlParser
    from eml_viewer.services.file_operation_service import FileOperationService
    from eml_viewer.services.settings_service import SettingsService
    from eml_viewer.services.update_service import UpdateService

    app = QApplication(argv)
    app.setApplicationName("EML Viewer")
    app.setOrganizationName("Local")
    app.setApplicationVersion(__version__)
    icon_path = _resource_path("assets/app.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    parser = EmlParser()
    file_operation_service = FileOperationService()
    window = MainWindow(
        parser=parser,
        attachment_service=AttachmentService(parser, file_operation_service),
        settings_service=SettingsService(),
        file_operation_service=file_operation_service,
        update_service=UpdateService(),
    )
    if not app.windowIcon().isNull():
        window.setWindowIcon(app.windowIcon())
    window.show()

    if len(argv) > 1:
        initial_path = Path(argv[1])
        if initial_path.suffix.lower() == ".eml":
            window.load_email(initial_path)

    return app.exec()
