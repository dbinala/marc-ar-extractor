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
st.write("청구기호(090 필드 a, b 정밀 패치) 버전입니다.")

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
                    
                    # 3. 청구기호(090 필드 전용 정밀 파싱 - ISBN 혼동 방지)
                    part_a = ""
                    part_b = ""
                    
                    # 레코드 내에서 '090' 필드가 시작되는 정확한 위치 혹은 라인을 탐색
                    # 020 필드와 구별하기 위해 '090' 태그 구조(공백이나 인디케이터 동반)를 타겟팅
                    field_090_match = re.search(r'(?:^|\n)\s*090.*?(?=\n\d{3}|\Z)', rec, re.DOTALL)
                    
                    target_chunk = ""
                    if field_090_match:
                        target_chunk = field_090_match.group(0)
                    elif '090' in rec:
                        # 대안: 090이 포함된 경우 그 주변부 150글자 확보
                        idx = rec.find('090')
                        target_chunk = rec[idx:idx+150]
                    
                    if target_chunk:
                        # a 서브필드 추출 (기존 도서관 청구기호 분류번호 패턴: 숫자 및 소수점 등)
                        a_sub = re.search(r'(?:[\x1f]a|a)\s*([0-9\.]+)', target_chunk)
                        if a_sub:
                            part_a = a_sub.group(1).strip()
                            
                        # b 서브필드 추출 (도서기호: 알파벳, 숫자, 특수문자 조합 허용)
                        b_sub = re.search(r'(?:[\x1f]b|b)\s*([A-Za-z0-9\-\.\s]+)', target_chunk)
                        if b_sub:
                            part_b = b_sub.group(1).strip()
                    
                    # 조합 만들기: [별치기호] [a숫자] [b문자]
                    call_parts = []
                    if location_label: call_parts.append(location_label)
                    if part_a: call_parts.append(part_a)
                    if part_b: call_parts.append(part_b)
                    
                    final_call = " ".join(call_parts)

                    def clean_text(text):
                        if not isinstance(text, str): return text
                        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text).strip()

                    data_list.append({
                        "청구기호": clean_text(final_call),
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
        else:
            st.warning("조건에 맞는 데이터를 찾지 못했습니다.")
