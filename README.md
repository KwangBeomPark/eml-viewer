# EML Viewer

Python과 PySide6로 만드는 Windows용 `.eml` 이메일 뷰어입니다.

초기 버전은 이메일 파일 1개를 안정적으로 열어 보는 기능에 집중합니다. 나중에 AI 요약, 자동 태그, 파일명 자동 변경, 폴더 단위 분석 기능을 붙일 수 있도록 화면 코드와 핵심 처리 코드를 분리했습니다.

## 주요 기능

- `.eml` 파일 선택 후 열기
- 제목, 보낸 사람, 받는 사람, 날짜 표시
- Plain Text 본문과 HTML 본문 구분 표시
- 첨부파일 목록 표시
- 첨부파일 저장
- 마지막 창 크기와 위치 저장
- 오류 발생 시 프로그램 종료 대신 메시지 표시

## 폴더 구조

```text
src/eml_viewer/
  app.py                     # 프로그램 시작과 전체 앱 설정
  gui/                       # 화면 코드
  models/                    # 데이터를 담는 단순한 클래스
  services/                  # EML 읽기, 첨부 저장, 설정 저장 같은 핵심 기능
  future/                    # 나중에 추가할 AI/파일명 변경/이력 기능 자리
```

## 개발 환경 준비

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## 실행

```powershell
python -m eml_viewer
```

또는 설치 후:

```powershell
eml-viewer
```

샘플 파일로 테스트하려면 프로그램에서 `samples\example_plain_text.eml` 파일을 열면 됩니다.

실행하면서 바로 파일을 열 수도 있습니다.

```powershell
python -m eml_viewer .\samples\example_plain_text.eml
```

## 테스트

```powershell
python -m unittest discover -s tests
```

## Windows 실행 파일 만들기

```powershell
python -m pip install -e ".[build]"
.\scripts\build_windows.ps1
```

결과물은 `dist\EmlViewer` 폴더에 생성됩니다.

## 설계 원칙

- 화면과 EML 처리 로직을 분리합니다.
- 파일 저장이나 이름 변경 같은 위험한 작업은 `미리 보기 -> 확인 -> 실행` 순서로 처리합니다.
- MVP에서는 외부 AI 패키지나 데이터베이스를 넣지 않습니다.
- HTML 메일은 배포 크기를 줄이기 위해 `QTextBrowser`로 표시합니다.

## 향후 확장 자리

- `src\eml_viewer\future\ai_analysis_service.py`: AI 요약, 키워드 추출, 업무 태그 추천
- `src\eml_viewer\future\rename_plan_service.py`: 파일명 자동 생성과 변경 전 미리 보기
- `src\eml_viewer\future\batch_scan_service.py`: 폴더 스캔과 여러 EML 파일 일괄 처리
- `src\eml_viewer\future\history_service.py`: 변경 이력 저장과 Undo
- `src\eml_viewer\future\update_service.py`: 향후 업데이트 확인 기능
- `packaging\inno`: 향후 Inno Setup 설치 패키지
