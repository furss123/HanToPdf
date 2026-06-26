# HanToPdf

한글 파일(.hwp, .hwpx)을 PDF로 변환하는 Windows 데스크톱 앱입니다.

## 기능

- 드래그앤드롭 / 파일 선택으로 한글 파일 추가
- 개별 PDF 또는 하나의 PDF로 병합
- 파일 이름 자동 정렬 (오름차순 / 내림차순)
- PDF 화질 설정 (원본화질 · 고화질 · 중간 · 저화질)
- 글래스모피즘 UI

## 요구 사항

- Windows 10/11
- Python 3.10+ (개발 시)
- 한컴오피스(한글) 설치

## 로컬 실행

```powershell
pip install -r requirements.txt
python main.py
```

## exe 빌드

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

바탕화면에 `HanToPdf.exe`와 바로가기가 생성됩니다.

## 프로젝트 구조

```
HanToPdf/
├── main.py          # UI (Tkinter)
├── converter.py     # HWP→PDF 변환 (COM)
├── settings.py      # 설정 저장
├── ui_theme.py      # 글래스모피즘 테마
└── build.ps1        # exe 빌드 스크립트
```

## 저작권

© HyoT. All rights reserved.
