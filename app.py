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
st.write("090 필드 강제 추출 정밀 패치 버전입니다.")

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
                    
                    # 2. 별치기호 (049 필드)
                    location_label = ""
                    f_match = re.search(r'(?:[\x1f]f|f)([A-Za-z0-9\-]+)', rec)
                    if f_match:
                        f_val = f_match.group(1).strip()
                        if f_val == 'KP': location_label = "원-유"
                        elif f_val == 'KC': location_label = "원아"
                        elif f_val == 'KE': location_label = "원서"
                        else: location_label = f_val
                    
                    # 3. 청구기호 (090 필드 강제 정밀 파싱)
                    part_a = ""
                    part_b = ""
                    
                    # 레코드 전체에서 '090'이 포함된 위치를 찾아, 그 주변(또는 090 이후 문자열)에서 a와 b 서브필드 패턴을 직접 탐색
                    if '090' in rec:
                        idx_090 = rec.find('090')
                        # 090부터 일정 길이(또는 다음 필드 전까지)의 청구기호 블록을 잘라냄
                        chunk_090 = rec[idx_090:idx_090+120]
                        
                        # 분류번호 $a (숫자와 소수점) 추출
                        a_match = re.search(r'(?:[\x1f]a|a)\s*([0-9]+(?:\.[0-9]+)?)', chunk_090)
                        if a_match:
                            part_a = a_match.group(1).strip()
                            
                        # 도서기호 $b 추출
                        b_match = re.search(r'(?:[\x1f]b|b)\s*([A-Za-z0-9\-\.]+)', chunk_090)
                        if b_match:
                            raw_b = b_match.group(1).strip()
                            # 불필요한 뒷부분이 딸려오는 것 방지
                            clean_b = re.match(r'([A-Za-z]+\d+[A-Za-z0-9\-\.]*)', raw_b)
                            if clean_b:
                                part_b = clean_b.group(1)
                            else:
                                part_b = raw_b

                    def clean_text(text):
                        if not isinstance(text, str): return text
                        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text).strip()

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
            st.warning("조건에 맞는 데이터를 찾지 못했습니다.")
