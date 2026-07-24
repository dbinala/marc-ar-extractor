import re
import pandas as pd
import streamlit as st
from PIL import Image

# 웹페이지 기본 설정
st.set_page_config(page_title="MARC AR Points 추출기", page_icon="📚", layout="centered")

# 로고 이미지 불러오기 (logo.png 파일이 있을 때만 표시)
try:
    img = Image.open("logo.png")
    st.image(img, width=150)
except Exception:
    pass 

st.title("📚 코라스 MARC AR Points 추출기")
st.write("코라스(KOLAS) 마크 파일에서 청구기호, 등록번호, AR Points를 자동으로 추출합니다.")

uploaded_file = st.file_uploader("마크(.TXT) 파일을 선택해주세요", type=["txt"])

if uploaded_file is not None:
    bytes_data = uploaded_file.read()
    full_text = None
    
    for enc in ['cp949', 'euc-kr', 'utf-8', 'utf-16']:
        try:
            full_text = bytes_data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
            
    if full_text is None:
        st.error("파일 인코딩을 인식할 수 없습니다. 파일 형식을 다시 확인해주세요.")
    else:
        records = re.split(r'[\x1d\n]+', full_text)
        data_list = []
        
        for rec in records:
            if 'AR' in rec or 'Pi' in rec or 'DJU' in rec or '090' in rec or '049' in rec:
                ar_match = re.search(r'AR\s*P[io]+nts?\s*[:]?\s*([\d\.]+)', rec, re.IGNORECASE)
                
                if ar_match:
                    ar_point = ar_match.group(1)
                    
                    # 1. 등록번호 추출 (DJU...)
                    reg_no_match = re.search(r'(DJU[A-Za-z0-9\-_]+)', rec)
                    reg_no = reg_no_match.group(1) if reg_no_match else ""
                    
                    # 2. 별치기호 추출 및 변환 (049 필드)
                    location_label = ""
                    f_match = re.search(r'(?:[\x1f]f|f)([A-Za-z0-9\-]+)', rec)
                    if f_match:
                        f_val = f_match.group(1).strip()
                        if f_val == 'KP':
                            location_label = "원-유"
                        elif f_val == 'KC':
                            location_label = "원아"
                        elif f_val == 'KE':
                            location_label = "원서"
                        else:
                            location_label = f_val
                    
                    # 3. 090 필드에서 엄격하게 a와 b 추출하기
                    part_a = ""
                    part_b = ""
                    
                    # 090 필드 블록만 정확히 잘라내기 (030, 020 등과 혼동 방지)
                    field_090_block = re.search(r'(?:^|\n|\x1e)\s*090\s*(.*?)(?=\n|\x1e|\d{3}\s|$)', rec, re.DOTALL)
                    if field_090_block:
                        block_text = field_090_block.group(1)
                        
                        # a 뒤의 숫자 추출 (예: 843)
                        sub_a_match = re.search(r'(?:[\x1f]a|a)\s*([0-9]+)', block_text)
                        if sub_a_match:
                            part_a = sub_a_match.group(1).strip()
                            
                        # b 뒤의 문자+숫자 조합 추출 (예: M644g) - 제어문자나 특수기호 전까지 깔끔하게
                        sub_b_match = re.search(r'(?:[\x1f]b|b)\s*([A-Za-z0-9]+)', block_text)
                        if sub_b_match:
                            part_b = sub_b_match.group(1).strip()

                    # 4. 요청하신 규칙대로 조합: [별치기호] [a뒤숫자] [b뒤문자숫자] (각각 한 칸 공백)
                    call_parts = []
                    if location_label:
                        call_parts.append(location_label)
                    if part_a:
                        call_parts.append(part_a)
                    if part_b:
                        call_parts.append(part_b)
                        
                    final_call_number = " ".join(call_parts)

                    # 제어 문자 제거 함수
                    def clean_text(text):
                        if not isinstance(text, str):
                            return text
                        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text).strip()

                    data_list.append({
                        "청구기호": clean_text(final_call_number),
                        "시작등록번호": clean_text(reg_no),
                        "AR_Points": clean_text(ar_point)
                    })
                    
        df = pd.DataFrame(data_list).drop_duplicates()
        
        if not df.empty:
            # 인덱스를 1부터 시작하도록 설정
            df.index = range(1, len(df) + 1)
            
            st.success(f"총 {len(df)}개의 데이터를 성공적으로 추출했습니다!")
            st.dataframe(df, use_container_width=True)
            
            excel_file = 'AR_Points_Extracted.xlsx'
            
            df_cleaned = df.map(lambda x: re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', str(x)) if pd.notnull(x) else x)
            df_cleaned.to_excel(excel_file, index=True, sheet_name="AR추출결과")
            
            with open(excel_file, "rb") as f:
                st.download_button(
                    label="📥 엑셀 파일 다운로드하기",
                    data=f,
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("추출된 데이터가 없습니다. 파일 내용을 다시 한 번 확인해 주세요.")
