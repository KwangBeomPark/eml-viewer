# AI_CODE_MAP.md - 프로젝트 전용 코드 지도

본 문서는 EML Viewer 프로젝트의 고유 구조, 기술 스택, 주요 기능 위치 및 변경 이력을 정리한 문서입니다.

## 1. 프로젝트 개요 및 실행 환경
- **프로젝트 목적**: Windows 환경을 위한 데스크톱 EML(이메일 파일) 뷰어 애플리케이션
- **제품 방향**: 단순 EML 열람기에서 시작해 메일 내용을 더 편하게 읽고, 첨부파일을 관리하고, 업데이트를 받을 수 있는 로컬 메일 생산성 도구로 확장합니다. 향후에는 설정 기반 SMTP 발송, 나에게 보내기/다른 사람에게 전달, 번역, 요약, 검색 같은 기능이 추가될 수 있으므로 GUI 위젯과 비즈니스 서비스의 경계를 유지합니다.
- **기술 스택**: Python 3.13, PySide6 (GUI), PyInstaller (단일 EXE 패키징), Inno Setup 6 (설치 프로그램 빌드)
- **실행 방법**:
  - 개발 실행: `.venv\Scripts\python -m eml_viewer` 또는 `.venv\Scripts\eml-viewer`
  - 테스트 실행: `.venv\Scripts\python -m unittest discover -s tests`

## 2. 폴더 구조 및 주요 파일 역할
```
eml-viewer/
├── myAGENT.md                      # 공통 개발 원칙 문서
├── AI_CODE_MAP.md                  # 프로젝트 전용 코드 지도 (본 문서)
├── assets/                         # 앱 아이콘 등 패키징/런타임 리소스
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
│       │   ├── metadata_widgets.py  # 제목/보낸 사람/받는 사람 복사 가능한 메타데이터 위젯
│       │   ├── message_widgets.py   # 본문 탭, CID 이미지 치환, 본문 확대/축소
│       │   ├── attachment_widgets.py # 첨부파일 요약/접힘/펼침/저장 UI
│       │   ├── settings_dialog.py   # 언어/테마 설정 대화상자
│       │   ├── theme.py             # 라이트/다크/시스템 테마 적용
│       │   ├── i18n.py              # eml_viewer.i18n 패키지 랩퍼 (호환성 유지용)
│       │   └── dialogs.py          # 공통 알림/선택 대화상자
│       ├── i18n/                    # 다국어(i18n) 패키지
│       │   ├── locales/             # JSON 번역 파일 (ko.json, en.json)
│       │   └── translator.py        # 다국어 번역 및 포맷팅 처리 모듈
│       └── services/               # 비즈니스 로직 레이어
│           ├── eml_parser.py       # EML 파일 파서 서비스
│           ├── settings_service.py  # 창 크기 및 기본 설정 서비스
│           └── update_service.py   # 업데이트 정보 확인 및 다운로드 서비스
└── tests/                          # 단위 테스트 폴더
```

## 3. 핵심 기능 및 클래스/함수 위치
- **애플리케이션 진입점**: `src/eml_viewer/app.py`의 `main()` 함수
- **메인 GUI 화면**: `src/eml_viewer/gui/main_window.py`의 `MainWindow` 클래스
- **메일 메타데이터 복사 UI**: `src/eml_viewer/gui/metadata_widgets.py`의 `CopyableLineEdit`
- **본문 표시 및 확대/축소**: `src/eml_viewer/gui/message_widgets.py`의 `MessageBodyWidget`
- **첨부파일 요약 및 저장 UI**: `src/eml_viewer/gui/attachment_widgets.py`의 `AttachmentPanel`
- **HTML-only 메일 텍스트 fallback 및 inline 이미지 분류**: `src/eml_viewer/services/eml_parser.py`의 `EmlParser`
- **언어/테마 설정 UI**: `src/eml_viewer/gui/settings_dialog.py`의 `SettingsDialog`, `src/eml_viewer/gui/theme.py`의 `apply_theme()`
- **업데이트 정보 확인**: `src/eml_viewer/services/update_service.py`의 `UpdateService.check_for_updates()`
- **업데이트 파일 다운로드**: `src/eml_viewer/services/update_service.py`의 `UpdateService.download_installer()`
- **백그라운드 다운로드 스레드**: `src/eml_viewer/gui/main_window.py`의 `DownloadThread` 클래스
- **인스톨러 설정**: `packaging/inno/eml_viewer.iss` (설치 관리자 생성 및 AppMutex 지정)

## 4. 특수 주의사항 및 리스크
- **최소 변경 원칙**: GUI와 비즈니스 로직(서비스)의 분리 상태를 훼손하지 않아야 합니다. `services` 패키지에서는 `PySide6` 라이브러리를 직접 호출하거나 가져오지 마십시오.
- **향후 기능 확장 경계**: SMTP 발송, 번역, 요약, 검색, 계정/서버 설정은 먼저 `services` 또는 별도 설정 모델에 도메인 로직을 두고, `gui` 레이어는 화면 조합과 사용자 입력/표시만 담당하도록 유지합니다.
- **설정 화면 확장 대비**: 기능이 늘어나면 `SettingsService`와 GUI 설정 패널을 분리해 관리하고, 메일 계정/SMTP 서버/포트/인증 정보 같은 민감 설정은 저장 방식과 노출 범위를 별도로 검토합니다.
- **업데이트 재설치 잠금 방지**: 업데이트가 완료된 후 새 인스톨러를 시작할 때 파일 쓰기 거부 에러를 방지하기 위해 `MainWindow`는 `os.startfile(dest_path)` 호출 후 `self.close()` → `QApplication.quit()`을 통해 정상 종료 흐름(`closeEvent` 포함)을 거칩니다. 또한 인스톨러 스크립트에 `AppMutex=EmlViewerMutex`와 `CloseApplications=yes`를 활성화해 두었으며, 이를 지원하기 위해 `src/eml_viewer/app.py`의 시작 단계에서 Windows 네임드 뮤텍스(`EmlViewerMutex`)를 직접 생성하여 소유권을 가집니다.
- **타임아웃 분리**: `UpdateService`는 API 확인용 타임아웃(`timeout_seconds=10`)과 대용량 파일 다운로드용 타임아웃(`download_timeout_seconds=300`)을 분리하여 관리합니다.

## 5. 변경 이력
### 2026-06-30
- **릴리즈 버전 업데이트 (0.1.4 -> 0.1.5)**:
  - 애플리케이션 패키지 버전, 프로젝트 메타데이터, Inno Setup 기본 버전을 `0.1.5`로 일괄 갱신.
  - Windows 인스톨러 릴리즈 산출물 생성을 위한 패치 버전 릴리즈 준비.

### 2026-06-29
- **다국어(i18n) 모듈 리팩토링 및 JSON locales 관리**:
  - 번역 데이터를 기존 Python 하드코딩 딕셔너리(`gui/i18n.py`)에서 독립된 JSON 파일(`i18n/locales/ko.json`, `i18n/locales/en.json`)로 이전하여 확장성 개선.
  - 신규 `eml_viewer.i18n` 패키지를 정의하고, `translator.py`에서 언어 설정, fallback 처리, 포맷팅 예외 대응을 전담하도록 구현.
  - 기존 코드의 호환성을 보장하기 위해 `gui/i18n.py`를 thin wrapper로 리팩토링.
  - 빌드 패키징 정보(`pyproject.toml`, `eml_viewer.spec`)를 업데이트하여 JSON 리소스가 정상적으로 동봉되도록 반영.
  - `tests/test_i18n.py`에 포괄적인 단위 테스트(7개 케이스)를 구축하여 번역 기능 및 로딩 일관성 검증 완료.
  - **버전 업데이트 (0.1.3 -> 0.1.4)**: `__init__.py`, `pyproject.toml`, `eml_viewer.iss` 및 관련 테스트 mock의 버전을 `0.1.4`로 일괄 갱신.

### 2026-06-26
- **HTML 본문/첨부/설정 UX 개선 2차 업데이트**:
  - `text/plain`이 없는 HTML-only 메일에서 표/중첩 표의 텍스트를 Plain Text 탭에 자동 생성해 표시.
  - HTML 본문 이미지 전처리를 `cid:`, URL 인코딩 CID, `Content-Location`, 상대 파일명, `background`, CSS `url(...)`까지 확장.
  - HTML에서 참조되는 이미지라면 `Content-Disposition: attachment`여도 본문 inline resource로 분류해 첨부 목록과 본문 표시가 충돌하지 않도록 보강.
  - 첨부파일 패널을 체크박스 다중 선택 기반으로 변경하고, 여러 파일 저장 시 폴더 선택 및 중복 파일명 자동 정리(`name (2).ext`)를 적용.
  - 설정 대화상자, 언어 설정(재시작 적용), 테마 설정(즉시 적용), 다크 모드 팔레트를 추가.
  - 실제 문제가 난 EML 샘플을 받으면 `tests/`에 fixture/회귀 테스트로 추가해 HTML 호환성 회귀를 막아야 함.

- **메일 읽기 UX 개선 1차 업데이트**:
  - 제목/보낸 사람/받는 사람 필드에 `CopyableLineEdit`을 적용해 우측 복사 버튼과 상태바 `Copied` 피드백을 추가.
  - 첨부파일 패널을 첨부가 없을 때 자동 숨김 처리하고, 첨부가 있을 때는 기본 접힘 요약(`Attachments N · size`)으로 표시하며 필요 시 펼쳐서 저장하도록 변경.
  - 본문 영역에 `Ctrl+마우스휠`, `Ctrl+0`, `- / + / 100%` 기반의 50~200% 확대/축소 흐름을 추가.
  - 앱 아이콘 리소스를 `assets/`에 추가하고 PyInstaller/Inno Setup/런타임 창 아이콘에 연결.
  - GitHub Releases 404 응답 시 “배포 버전 없음” 단정 대신 저장소 접근권한/릴리스 공개 상태를 확인할 수 있는 문구로 개선.

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
