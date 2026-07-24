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
st.write("코라스(KOLAS) 마크 파일에서 통합 청구기호, 등록번호, AR Points를 자동으로 추출합니다.")

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
                    
                    # 3. 청구기호 추출 (090 필드 - 더 유연하게 탐색)
                    call_number_body = ""
                    # 090 필드 이후의 데이터를 유연하게 가져옴
                    field_090_match = re.search(r'090.*?([a-zA-Z0-9\-_/\.]+)', rec)
                    
                    # 서브필드 a, b를 직접 정밀 탐색
                    sub_a_match = re.search(r'(?:[\x1f]a|a)([^\x1f\n\t\x1e]+)', rec)
                    sub_b_match = re.search(r'(?:[\x1f]b|b)([^\x1f\n\t\x1e]+)', rec)
                    
                    part_a = sub_a_match.group(1).strip() if sub_a_match else ""
                    part_b = sub_b_match.group(1).strip() if sub_b_match else ""
                    
                    if part_a or part_b:
                        call_number_body = f"{part_a}{part_b}"
                    else:
                        # 만약 위 방식으로 안 잡히면 090 뒤쪽 문자열 대안 탐색
                        alt_090 = re.search(r'090\s*.*?([^\x1f\x1e\n]+)', rec)
                        if alt_090:
                            call_number_body = alt_090.group(1).strip()

                    # 4. 별치기호와 청구기호 결합 (예: 원-유 843M649m)
                    if location_label and call_number_body:
                        final_call_number = f"{location_label} {call_number_body}"
                    elif location_label:
                        final_call_number = location_label
                    else:
                        final_call_number = call_number_body

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
            # 인덱스를 0부터가 아니라 1부터 시작하도록 설정 (+1)
            df.index = range(1, len(df) + 1)
            
            st.success(f"총 {len(df)}개의 데이터를 성공적으로 추출했습니다!")
            st.dataframe(df, use_container_width=True)
            
            excel_file = 'AR_Points_Extracted.xlsx'
            
            df_cleaned = df.map(lambda x: re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', str(x)) if pd.notnull(x) else x)
            df_cleaned.to_excel(excel_file, index=True, sheet_name="AR추출결과") # 엑셀에도 1부터 시작하는 번호가 포함되도록 저장
            
            with open(excel_file, "rb") as f:
                st.download_button(
                    label="📥 엑셀 파일 다운로드하기",
                    data=f,
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("추출된 데이터가 없습니다. 파일 내용을 다시 한 번 확인해 주세요.")
