import streamlit as st
import re
import pandas as pd

def parse_marc_record(record_text):
    """
    단일 MARC 레코드 텍스트에서 049(별치기호 등)와 090(청구기호) 필드를 안전하게 파싱하는 함수
    """
    shelf_location = ""  # 별치기호 (049 필드 등에서 추출)
    call_number = ""     # 청구기호 (090 필드)
    
    lines = record_text.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 049 필드 처리
        if line.startswith("049"):
            f_match = re.search(r'\$f\s*([^\$\t]+)', line)
            if f_match:
                shelf_location = f_match.group(1).strip()
            
        # 090 필드 처리
        elif line.startswith("090"):
            sub_a = re.search(r'\$a\s*([^\$\t]+)', line)
            sub_b = re.search(r'\$b\s*([^\$\t]+)', line)
            
            a_val = sub_a.group(1).strip() if sub_a else ""
            b_val = sub_b.group(1).strip() if sub_b else ""
            
            if a_val and b_val:
                call_number = f"{a_val} {b_val}"
            elif a_val:
                call_number = a_val
            elif b_val:
                call_number = b_val
                
    return shelf_location, call_number


def process_marc_content(content):
    """
    마크 파일 전체 내용을 읽어와 레코드별로 파싱하는 함수
    """
    results = []
    
    # 레코드 구분 (빈 줄이나 표준 구분자 기준)
    records = re.split(r'\n\s*\n', content)
    
    for idx, record in enumerate(records):
        if not record.strip():
            continue
            
        shelf, call = parse_marc_record(record)
        
        # 2차 보완 탐색 (데이터 누락 방지)
        if not call:
            match_090 = re.search(r'090.*?\$a([^\$]+)(?:\$b([^\$]+))?', record)
            if match_090:
                part1 = match_090.group(1).strip() if match_090.group(1) else ""
                part2 = match_090.group(2).strip() if match_090.group(2) else ""
                call = f"{part1} {part2}".strip()

        results.append({
            'No': idx + 1,
            '별치기호': shelf,
            '청구기호': call
        })
        
    return results


# Streamlit UI 구성
st.title("📚 MARC 파일 별치 및 청구기호 추출기")
st.write("코라스(KOLAS) 등에서 반출된 MARC 파일을 업로드하면 별치기호와 청구기호를 깔끔하게 추출해 드립니다.")

uploaded_file = st.file_uploader("MARC(.mrc 또는 .txt) 파일을 업로드하세요", type=["mrc", "txt"])

if uploaded_file is not None:
    try:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    except Exception:
        content = uploaded_file.getvalue().decode("cp949", errors="ignore")
        
    if st.button("데이터 추출 실행"):
        parsed_data = process_marc_content(content)
        
        if parsed_data:
            df = pd.DataFrame(parsed_data)
            st.success(f"총 {len(df)}개의 레코드를 성공적으로 읽어왔습니다!")
            st.dataframe(df)
            
            # 엑셀 다운로드 버튼
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="결과 엑셀(CSV) 다운로드",
                data=csv,
                file_name="parsed_marc_result.csv",
                mime="text/csv",
            )
        else:
            st.warning("추출된 데이터가 없습니다. 파일 형식을 다시 확인해 주세요.")
