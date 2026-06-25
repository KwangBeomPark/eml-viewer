# AI_CODE_MAP.md - 프로젝트 전용 코드 지도

본 문서는 EML Viewer 프로젝트의 고유 구조, 기술 스택, 주요 기능 위치 및 변경 이력을 정리한 문서입니다.

## 1. 프로젝트 개요 및 실행 환경
- **프로젝트 목적**: Windows 환경을 위한 데스크톱 EML(이메일 파일) 뷰어 애플리케이션
- **기술 스택**: Python 3.13, PySide6 (GUI), PyInstaller (단일 EXE 패키징), Inno Setup 6 (설치 프로그램 빌드)
- **실행 방법**:
  - 개발 실행: `.venv\Scripts\python -m eml_viewer` 또는 `.venv\Scripts\eml-viewer`
  - 테스트 실행: `.venv\Scripts\python -m unittest discover -s tests`

## 2. 폴더 구조 및 주요 파일 역할
```
eml-viewer/
├── myAGENT.md                      # 공통 개발 원칙 문서
├── AI_CODE_MAP.md                  # 프로젝트 전용 코드 지도 (본 문서)
├── pyproject.toml                  # 프로젝트 빌드 구성 및 종속성 관리
├── packaging/
│   ├── pyinstaller/                # PyInstaller spec 파일 위치
│   └── inno/                       # Inno Setup 스크립트 (eml_viewer.iss)
├── scripts/                        # 빌드 및 인스톨러 생성 파워쉘 스크립트
├── src/
│   └── eml_viewer/
│       ├── app.py                  # 프로그램 시작 진입점 및 예외 처리
│       ├── gui/                    # GUI 레이어
│       │   ├── main_window.py      # 메인 화면 및 업데이트 다운로드 연동
│       │   └── dialogs.py          # 공통 알림/선택 대화상자
│       └── services/               # 비즈니스 로직 레이어
│           ├── eml_parser.py       # EML 파일 파서 서비스
│           ├── settings_service.py  # 창 크기 및 기본 설정 서비스
│           └── update_service.py   # 업데이트 정보 확인 및 다운로드 서비스
└── tests/                          # 단위 테스트 폴더
```

## 3. 핵심 기능 및 클래스/함수 위치
- **애플리케이션 진입점**: `src/eml_viewer/app.py`의 `main()` 함수
- **메인 GUI 화면**: `src/eml_viewer/gui/main_window.py`의 `MainWindow` 클래스
- **업데이트 정보 확인**: `src/eml_viewer/services/update_service.py`의 `UpdateService.check_for_updates()`
- **업데이트 파일 다운로드**: `src/eml_viewer/services/update_service.py`의 `UpdateService.download_installer()`
- **백그라운드 다운로드 스레드**: `src/eml_viewer/gui/main_window.py`의 `DownloadThread` 클래스
- **인스톨러 설정**: `packaging/inno/eml_viewer.iss` (설치 관리자 생성 및 AppMutex 지정)

## 4. 특수 주의사항 및 리스크
- **최소 변경 원칙**: GUI와 비즈니스 로직(서비스)의 분리 상태를 훼손하지 않아야 합니다. `services` 패키지에서는 `PySide6` 라이브러리를 직접 호출하거나 가져오지 마십시오.
- **업데이트 재설치 잠금 방지**: 업데이트가 완료된 후 새 인스톨러를 시작할 때 파일 쓰기 거부 에러를 방지하기 위해 `MainWindow`는 `os.startfile(dest_path)` 호출 후 `self.close()` → `QApplication.quit()`을 통해 정상 종료 흐름(`closeEvent` 포함)을 거칩니다. 또한 인스톨러 스크립트에 `AppMutex=EmlViewerMutex`와 `CloseApplications=yes`를 활성화해 두었으며, 이를 지원하기 위해 `src/eml_viewer/app.py`의 시작 단계에서 Windows 네임드 뮤텍스(`EmlViewerMutex`)를 직접 생성하여 소유권을 가집니다.
- **타임아웃 분리**: `UpdateService`는 API 확인용 타임아웃(`timeout_seconds=10`)과 대용량 파일 다운로드용 타임아웃(`download_timeout_seconds=300`)을 분리하여 관리합니다.

## 5. 변경 이력
### 2026-06-25
- **업데이트 자동 다운로드 및 재설치 기능 구현**:
  - `UpdateService`에 청크 단위의 설치 파일 다운로드 및 취소(`threading.Event`), 실시간 콜백 지원 기능 추가.
  - `MainWindow` 내에 다운로드 진행을 비동기로 처리할 `DownloadThread` 구현.
  - GUI 업데이트 확인 시 브라우저 이동 대신 확인을 거쳐 `QProgressDialog`를 띄워 임시 경로에 인스톨러 다운로드.
  - 다운로드 완료 시 인스톨러를 호출하고 자신은 프로세스를 바로 종료하도록 연동.
  - Inno Setup 스크립트에 `AppMutex` 및 `CloseApplications` 명시하여 실행 중 파일 잠김 및 재설치 차단 방지.
  - 신규 다운로드 및 취소 로직을 검증하기 위한 단위 테스트(`tests/test_update_download.py`) 작성.
- **프로세스 감지 및 다운로드 유효성 검사 등 방어적 보완 추가**:
  - `app.py` 시작 시 Windows 네임드 뮤텍스(`EmlViewerMutex`)를 생성해 인스톨러의 `AppMutex` 프로세스 중단이 정상 작동되도록 지원.
  - `main_window.py` 내 다운로드 완료 콜백(`_on_download_finished`)에 파일의 존재 여부 및 0바이트 초과 크기 검증 로직 추가.
  - `eml_viewer.iss` 스크립트에서 바탕화면 바로가기 단축 아이콘 기본 생성 유무(`Flags: unchecked` 제거)를 기본 체크(`checked`) 상태로 상향 설정.
- **코드 품질 개선**:
  - `main_window.py`: 업데이트 후 종료 시 `sys.exit(0)` 대신 `self.close()` → `QApplication.quit()` 사용으로 `closeEvent` 정상 호출 보장 (창 설정 저장 누락 방지).
  - `update_service.py`: API 확인용 `timeout_seconds`(10초)와 다운로드용 `download_timeout_seconds`(300초) 분리로 대용량 파일 다운로드 시 타임아웃 방지.
  - `build_installer.ps1`: PowerShell 인코딩 문제를 방지하기 위해 한글 오류 메시지를 영문으로 변경.

