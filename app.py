# ==============================
# app.py
# KORAS MARC AR Extractor
# Part 1
# ==============================

import re
from io import BytesIO

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="KORAS MARC AR Extractor",
    page_icon="📚",
    layout="wide"
)

st.title("📚 KORAS MARC AR Extractor")
st.caption("049 / 090 / 521 필드를 이용하여 AR 데이터를 추출합니다.")

uploaded_file = st.file_uploader(
    "반출마크 TXT(MARC) 파일 선택",
    type=["txt", "TXT"]
)

# -----------------------------
# 인코딩 자동 감지
# -----------------------------

def read_file(upload):

    raw = upload.read()

    encodings = [
        "cp949",
        "euc-kr",
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be"
    ]

    for enc in encodings:
        try:
            return raw.decode(enc)
        except:
            pass

    return raw.decode(
        "cp949",
        errors="ignore"
    )

# -----------------------------
# 코드 변환
# -----------------------------

LOCATION_MAP = {

    "KE":"원서",

    "KP":"원-유",

    "KC":"원-아",

    "KD":"원-초",

    "KF":"원-청",

    "KG":"원-일반"

}

def convert_location(code):

    if code in LOCATION_MAP:
        return LOCATION_MAP[code]

    return code

# -----------------------------
# AR Point 추출
# -----------------------------

def extract_ar(record):

    m = re.search(
        r"AR\s*Pionts?\s*:\s*([0-9.]+)",
        record,
        re.I
    )

    if m:
        return m.group(1)

    return ""

# -----------------------------
# 090 추출
# -----------------------------

def extract_call_number(record):

    class_no = ""

    book_no = ""

    m = re.search(
        r"090.*?\x1fa([^\x1f\x1e]+)",
        record,
        re.S
    )

    if m:
        class_no = m.group(1).strip()

    m = re.search(
        r"090.*?\x1fb([^\x1f\x1e]+)",
        record,
        re.S
    )

    if m:
        book_no = m.group(1).strip()

    call_no = f"{class_no} {book_no}".strip()

    return class_no, book_no, call_no
    # -----------------------------
# 049 추출 (등록번호 + 별치기호)
# -----------------------------

def extract_items(record):

    items = []

    idx = record.find("049")

    if idx == -1:
        return items

    end = record.find("\x1e", idx)

    if end == -1:
        end = len(record)

    field049 = record[idx:end]

    regs = re.findall(
        r"\x1fl([^\x1f\x1e]+)",
        field049
    )

    locs = re.findall(
        r"\x1ff([^\x1f\x1e]+)",
        field049
    )

    if len(regs) == 0:
        return items

    for i, reg in enumerate(regs):

        loc = ""

        if i < len(locs):
            loc = convert_location(locs[i])

        items.append(
            {
                "등록번호": reg.strip(),
                "별치기호": loc
            }
        )

    return items


# -----------------------------
# 레코드 파싱
# -----------------------------

def parse_record(record):

    ar = extract_ar(record)

    class_no, book_no, call_no = extract_call_number(record)

    items = extract_items(record)

    rows = []

    if len(items) == 0:

        rows.append(
            {
                "등록번호":"",
                "별치기호":"",
                "분류번호":class_no,
                "도서기호":book_no,
                "청구기호":call_no,
                "AR Points":ar
            }
        )

        return rows

    for item in items:

        rows.append(
            {
                "등록번호":item["등록번호"],
                "별치기호":item["별치기호"],
                "분류번호":class_no,
                "도서기호":book_no,
                "청구기호":call_no,
                "AR Points":ar
            }
        )

    return rows


# -----------------------------
# 전체 레코드 분리
# -----------------------------

def split_records(text):

    records = []

    for rec in text.split("\x1d"):

        rec = rec.strip()

        if len(rec) == 0:
            continue

        records.append(rec)

    return records
    # -----------------------------
# 메인 처리
# -----------------------------

if uploaded_file is not None:

    text = read_file(uploaded_file)

    records = split_records(text)

    result = []

    progress = st.progress(0)

    total = len(records)

    for i, rec in enumerate(records):

        result.extend(parse_record(rec))

        if total > 0:
            progress.progress((i + 1) / total)

    df = pd.DataFrame(result)

    # 중복 제거
    df = df.drop_duplicates()

    # 등록번호 기준 정렬
    if "등록번호" in df.columns:
        df = df.sort_values(
            by="등록번호",
            ignore_index=True
        )

    st.success(f"{len(df):,}건 추출 완료")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------
    # 통계
    # -----------------------------

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "등록번호",
            f"{len(df):,}"
        )

    with c2:
        ar_count = (
            df["AR Points"]
            .astype(str)
            .replace("", pd.NA)
            .dropna()
            .count()
        )

        st.metric(
            "AR 보유",
            f"{ar_count:,}"
        )

    with c3:
        st.metric(
            "별치기호 종류",
            df["별치기호"].nunique()
        )

    # -----------------------------
    # Excel 저장
    # -----------------------------

    excel = BytesIO()

    with pd.ExcelWriter(
        excel,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="AR"
        )

        ws = writer.sheets["AR"]

        for cell in ws[1]:
            cell.font = cell.font.copy(bold=True)

        for col in ws.columns:

            length = 0

            column = col[0].column_letter

            for cell in col:

                try:
                    length = max(
                        length,
                        len(str(cell.value))
                    )
                except:
                    pass

            ws.column_dimensions[column].width = min(length + 4, 35)

    excel.seek(0)

    st.download_button(
        "📥 Excel 다운로드",
        excel,
        file_name="AR_Extract.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
