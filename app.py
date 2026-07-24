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
st.write("코라스(KOLAS) 마크 파일에서 별치기호, 청구기호, 등록번호, AR Points를 자동으로 추출합니다.")

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
                    
                    # 2. 별치기호 추출 (049 필드 안의 f 값 변환)
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
                    
                    # 3. 청구기호 추출 (오직 090 필드가 명확히 있는 경우에만 a와 b 조합)
                    call_number = ""
                    # 090 필드 영역을 정확히 타겟팅 (다른 필드 020 등이 섞이지 않도록 함)
                    field_090_match = re.search(r'(?:^|\n|\x1e)\s*090\s*(.*?)(?=\n|\x1e|\d{3}\s|$)', rec, re.DOTALL)
                    if field_090_match:
                        f090_text = field_090_match.group(1)
                        sub_a_match = re.search(r'(?:[\x1f]a|a)([^\x1f\n\t]+)', f090_text)
                        sub_b_match = re.search(r'(?:[\x1f]b|b)([^\x1f\n\t]+)', f090_text)
                        
                        part_a = sub_a_match.group(1).strip() if sub_a_match else ""
                        part_b = sub_b_match.group(1).strip() if sub_b_match else ""
                        
                        if part_a and part_b:
                            call_number = f"{part_a}{part_b}"
                        elif part_a:
                            call_number = part_a
                        elif part_b:
                            call_number = part_b

                    # 제어 문자 제거 함수
                    def clean_text(text):
                        if not isinstance(text, str):
                            return text
                        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text).strip()

                    data_list.append({
                        "별치기호": clean_text(location_label),
                        "청구기호": clean_text(call_number),
                        "시작등록번호": clean_text(reg_no),
                        "AR_Points": clean_text(ar_point)
                    })
                    
        df = pd.DataFrame(data_list).drop_duplicates()
        
        if not df.empty:
            st.success(f"총 {len(df)}개의 데이터를 성공적으로 추출했습니다!")
            st.dataframe(df, use_container_width=True)
            
            excel_file = 'AR_Points_Extracted.xlsx'
            
            # 최신 판다스 버전 호환을 위해 applymap 대신 map 사용
            df_cleaned = df.map(lambda x: re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', str(x)) if pd.notnull(x) else x)
            df_cleaned.to_excel(excel_file, index=False)
            
            with open(excel_file, "rb") as f:
                st.download_button(
                    label="📥 엑셀 파일 다운로드하기",
                    data=f,
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("추출된 데이터가 없습니다. 파일 내용을 다시 한 번 확인해 주세요.")
