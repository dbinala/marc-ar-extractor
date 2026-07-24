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
st.write("MARC 디렉토리 및 필드 구조 정밀 대응 버전입니다.")

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
        # MARC 레코드 단위 구분자('\x1d' 또는 레코드 시작 기호)로 분리
        records = re.split(r'[\x1d]+', full_text)
        data_list = []
        
        for rec in records:
            if not rec.strip():
                continue
                
            # 디렉토리 숫자 영역과 실제 본문 영역 분리 
            # (보통 001~999 같은 태그 번호나 '' 기호, 혹은 KMO 등의 문자열을 기준으로 본문 영역을 식별)
            body_text = rec
            if '' in rec:
                parts = rec.split('', 1)
                if len(parts) > 1:
                    body_text = parts[1] # 실제 데이터 영역만 추출
            
            # 본문 전체에서 필요한 데이터 탐색
            if 'AR' in body_text or 'Pi' in body_text or 'DJU' in body_text or '090' in body_text or '049' in body_text or '521' in body_text:
                
                # 1. AR Points 추출 (521 필드 등)
                ar_match = re.search(r'AR\s*P[io]+nts?\s*[:]?\s*([\d\.]+)', body_text, re.IGNORECASE)
                ar_point = ar_match.group(1) if ar_match else ""
                
                # 2. 등록번호 추출
                reg_no_match = re.search(r'(DJU[A-Za-z0-9\-_]+)', body_text)
                reg_no = reg_no_match.group(1) if reg_no_match else ""
                
                # 3. 별치기호 추출 (049 필드 $f)
                location_label = ""
                f_match = re.search(r'(?:[\x1f]f|f)([A-Za-z0-9\-]+)', body_text)
                if f_match:
                    f_val = f_match.group(1).strip()
                    if f_val == 'KP': location_label = "원-유"
                    elif f_val == 'KC': location_label = "원아"
                    elif f_val == 'KE': location_label = "원서"
                    else: location_label = f_val
                
                # 4. 청구기호 추출 (090 필드 $a, $b)
                part_a = ""
                part_b = ""
                
                # 090 필드 영역 탐색
                if '090' in body_text:
                    idx_090 = body_text.find('090')
                    chunk_090 = body_text[idx_090:idx_090+100]
                    
                    # 분류번호 $a (숫자 및 소수점)
                    a_match = re.search(r'(?:[\x1f]a|a)\s*([0-9]+(?:\.[0-9]+)?)', chunk_090)
                    if a_match:
                        part_a = a_match.group(1).strip()
                        
                    # 도서기호 $b (알파벳, 숫자 조합)
                    b_match = re.search(r'(?:[\x1f]b|b)\s*([A-Za-z0-9\-\.]+)', chunk_090)
                    if b_match:
                        raw_b = b_match.group(1).strip()
                        clean_b = re.match(r'([A-Za-z]+\d+[A-Za-z0-9\-\.]*)', raw_b)
                        if clean_b:
                            part_b = clean_b.group(1)
                        else:
                            part_b = raw_b

                def clean_text(text):
                    if not isinstance(text, str): return text
                    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text).strip()

                # 데이터가 유효한 경우에만 리스트에 추가
                if reg_no or ar_point or part_a:
                    data_list.append({
                        "별치기호": clean_text(location_label),
                        "분류번호(090 $a)": clean_text(part_a),
                        "도서기호(090 $b)": clean_text(part_b),
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
            st.warning("조건에 맞는 데이터를 찾지 못했습니다. 파일 구조를 확인해 주세요.")
