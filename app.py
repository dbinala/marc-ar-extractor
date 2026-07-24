import re
import pandas as pd
import streamlit as st
from PIL import Image

# 웹페이지 기본 설정
st.set_page_config(page_title="MARC AR Points 추출기", page_icon="📚", layout="centered")

try:
    img = Image.open("logo.png")
    st.image(img, width=150)
except Exception:
    pass 

st.title("📚 코라스 MARC AR Points 추출기")
st.write("090 필드 격리 테스트 중입니다.")

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
        st.error("파일 인코딩을 인식할 수 없습니다.")
    else:
        records = re.split(r'[\x1d\n]+', full_text)
        data_list = []
        
        for rec in records:
            if 'AR' in rec or 'Pi' in rec or 'DJU' in rec or '090' in rec or '049' in rec:
                ar_match = re.search(r'AR\s*P[io]+nts?\s*[:]?\s*([\d\.]+)', rec, re.IGNORECASE)
                
                if ar_match:
                    ar_point = ar_match.group(1)
                    
                    # 1. 등록번호
                    reg_no_match = re.search(r'(DJU[A-Za-z0-9\-_]+)', rec)
                    reg_no = reg_no_match.group(1) if reg_no_match else ""
                    
                    # 2. 별치기호
                    location_label = ""
                    f_match = re.search(r'(?:[\x1f]f|f)([A-Za-z0-9\-]+)', rec)
                    if f_match:
                        f_val = f_match.group(1).strip()
                        if f_val == 'KP': location_label = "원-유"
                        elif f_val == 'KC': location_label = "원아"
                        elif f_val == 'KE': location_label = "원서"
                        else: location_label = f_val
                    
                    # 3. [핵심수정] 오직 '090'이 포함된 블록/라인 내부에서만 a 뒤 숫자 찾기 (ISBN 020 차단)
                    part_a = ""
                    # 레코드를 줄 단위로 쪼개서 '090'이라는 단어가 정확히 들어간 줄만 색출
                    lines = rec.split('\n')
                    for line in lines:
                        # 020 등 다른 필드가 포함된 줄은 무시하고 정확히 090 필드인 경우만 타겟
                        if '090' in line and '020' not in line:
                            a_match = re.search(r'(?:[\x1f]a|a)\s*([0-9]+)', line)
                            if a_match:
                                part_a = a_match.group(1)
                                break
                    
                    # 만약 줄 단위로 못 찾았을 경우, 정규식으로 090 뒤에 오는 a값만 엄격히 격리 추출
                    if not part_a:
                        strict_090 = re.search(r'090[^\n\x1e]*?(?:[\x1f]a|a)\s*([0-9]+)', rec)
                        if strict_090:
                            part_a = strict_090.group(1)

                    # 최종 결합 테스트
                    test_call = f"{location_label} {part_a}".strip() if part_a else location_label

                    def clean_text(text):
                        if not isinstance(text, str): return text
                        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text).strip()

                    data_list.append({
                        "청구기호(테스트)": clean_text(test_call),
                        "시작등록번호": clean_text(reg_no),
                        "AR_Points": clean_text(ar_point)
                    })
                    
        df = pd.DataFrame(data_list).drop_duplicates()
        
        if not df.empty:
            df.index = range(1, len(df) + 1)
            st.success(f"총 {len(df)}개 추출 성공!")
            st.dataframe(df, use_container_width=True)
            
            excel_file = 'AR_Points_Extracted.xlsx'
            df_cleaned = df.map(lambda x: re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', str(x)) if pd.notnull(x) else x)
            df_cleaned.to_excel(excel_file, index=True)
            
            with open(excel_file, "rb") as f:
                st.download_button(label="📥 엑셀 다운로드", data=f, file_name=excel_file)
