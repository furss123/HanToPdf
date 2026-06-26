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

## GitHub 연동 · 온라인 작업

| 방법 | 용도 |
|------|------|
| [GitHub 저장소](https://github.com) | 코드 관리, 이슈, PR |
| [GitHub Pages](docs/index.html) | 프로젝트 소개 페이지 (자동 배포) |
| [GitHub Codespaces](https://github.com/codespaces) | 브라우저에서 코드 편집·개발 |

### 저장소 최초 연동

```powershell
gh auth login
gh repo create HanToPdf --public --source=. --remote=origin --push
```

GitHub Pages 설정: **Settings → Pages → Build and deployment → GitHub Actions**

### 온라인에서 가능한 것 / 불가능한 것

- ✅ 코드 수정, PR, Issues, 프로젝트 페이지
- ✅ Codespaces에서 Python 개발 환경 사용
- ❌ 브라우저에서 HWP→PDF 변환 (한글 COM은 Windows 로컬 전용)

## 프로젝트 구조

```
HanToPdf/
├── main.py          # UI (Tkinter)
├── converter.py     # HWP→PDF 변환 (COM)
├── settings.py      # 설정 저장
├── ui_theme.py      # 글래스모피즘 테마
├── build.ps1        # exe 빌드 스크립트
└── docs/            # GitHub Pages
```

## 라이선스

MIT (필요 시 추가)
