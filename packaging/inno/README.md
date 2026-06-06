# Inno Setup packaging placeholder

MVP는 PyInstaller `onedir` 실행 파일만 만듭니다.

향후 설치 프로그램이 필요해지면 이 폴더에 Inno Setup 스크립트를 추가합니다.

예정 흐름:

1. PyInstaller로 `dist\EmlViewer` 생성
2. Inno Setup으로 시작 메뉴, 바탕화면 바로가기, 제거 프로그램 생성
3. 업데이트 확인 기능과 버전 정보를 연결
