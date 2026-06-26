"""바탕화면에 샘플 한글(HWPX) 파일 10개 생성."""

from __future__ import annotations

import zipfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED

DESKTOP = Path.home() / "Desktop"
SAMPLE_DIR = DESKTOP / "HanToPdf_샘플"

NAMES = [
    "01_회의록_샘플",
    "02_보고서_샘플",
    "03_견적서_샘플",
    "04_공문_샘플",
    "05_안내문_샘플",
    "06_계획서_샘플",
    "07_제안서_샘플",
    "08_확인서_샘플",
    "09_목록_샘플",
    "10_테스트_샘플",
]

SECTION0 = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hs:sec xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app"
 xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
 xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"
 xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">
  <hp:p id="0" paraPrIDRef="0" styleIDRef="0">
    <hp:run charPrIDRef="0">
      <hp:t>{title}</hp:t>
    </hp:run>
  </hp:p>
  <hp:p id="1" paraPrIDRef="0" styleIDRef="0">
    <hp:run charPrIDRef="0">
      <hp:t>HanToPdf 변환 테스트용 샘플 문서입니다.</hp:t>
    </hp:run>
  </hp:p>
</hs:sec>
"""

HEADER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"
 xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
 xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">
  <hh:refList>
    <hh:fontfaces itemCnt="1">
      <hh:fontface lang="HANGUL" fontCnt="1">
        <hh:font id="0" face="맑은 고딕" type="TTF" isEmbedded="0"/>
      </hh:fontface>
    </hh:fontfaces>
    <hh:charProperties itemCnt="1">
      <hh:charPr id="0" height="1000" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="0">
        <hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
      </hh:charPr>
    </hh:charProperties>
    <hh:paraProperties itemCnt="1">
      <hh:paraPr id="0" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="1" suppressLineNumbers="0" checked="0">
        <hh:align horizontal="LEFT" vertical="BASELINE"/>
        <hh:heading type="NONE" idRef="0" level="0"/>
        <hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>
        <hh:autoSpacing eAsianEng="0" eAsianNum="0"/>
        <hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>
      </hh:paraPr>
    </hh:paraProperties>
  </hh:refList>
</hh:head>
"""

CONTENT_HPF = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<opf:package xmlns:opf="http://www.idpf.org/2007/opf/">
  <opf:metadata>
    <opf:title>{title}</opf:title>
  </opf:metadata>
  <opf:manifest>
    <opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>
    <opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>
  </opf:manifest>
  <opf:spine>
    <opf:itemref idref="section0"/>
  </opf:spine>
</opf:package>
"""

CONTAINER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container">
  <ocf:rootfiles>
    <ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>
  </ocf:rootfiles>
</ocf:container>
"""

VERSION = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" tagetApplication="WORDPROCESSOR" major="5" minor="1" patch="1" build="0" os="1" xmlVersion="1.4" application="HanToPdf Sample"/>
"""


def _write_hwpx(path: Path, title: str) -> None:
    files = {
        "mimetype": "application/hwp+zip",
        "version.xml": VERSION,
        "Contents/header.xml": HEADER,
        "Contents/section0.xml": SECTION0.format(title=title),
        "Contents/content.hpf": CONTENT_HPF.format(title=title),
        "META-INF/container.xml": CONTAINER,
        "Preview/PrvText.txt": f"{title}\nHanToPdf 샘플",
    }
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", files["mimetype"], compress_type=ZIP_STORED)
        for name, data in files.items():
            if name == "mimetype":
                continue
            zf.writestr(name, data.encode("utf-8"), compress_type=ZIP_DEFLATED)


def create_samples() -> Path:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        _write_hwpx(SAMPLE_DIR / f"{name}.hwpx", name.replace("_", " "))
    return SAMPLE_DIR


if __name__ == "__main__":
    folder = create_samples()
    print(f"생성 완료: {folder}")
    for p in sorted(folder.glob("*.hwpx")):
        print(f"  {p.name}")
