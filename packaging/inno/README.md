# Inno Setup packaging

이 폴더는 Windows 설치 파일을 만들기 위한 Inno Setup 설정을 담습니다.

## 필요 도구

- Inno Setup 6
- Python 개발 환경
- PyInstaller

## 빌드

```powershell
.\scripts\build_installer.ps1
```

결과 파일:

```text
installer\EmlViewerSetup-0.1.0.exe
```

설치 파일은 `.eml` 더블클릭 연결을 선택 항목으로 제공합니다.
