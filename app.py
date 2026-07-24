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
        # ISO2709 레코드 구분자(\x1d 또는 줄바꿈)로 분리
        records = re.split(r'[\x1d\n]+', full_text)
        data_list = []
        
        for rec in records:
            if not rec.strip():
                continue
            
            # ISO2709 정식 구조 파싱 (Leader(24바이트) + Directory(12바이트씩) + \x1e + Variable Fields)
            if len(rec) > 24:
                leader = rec[:24]
                idx_sep = rec.find('\x1e')
                if idx_sep != -1:
                    directory_part = rec[24:idx_sep]
                    variable_fields_part = rec[idx_sep+1:]
                else:
                    directory_part = ""
                    variable_fields_part = rec[24:]
                
                fields = []
                for i in range(0, len(directory_part), 12):
                    entry = directory_part[i:i+12]
                    if len(entry) < 12:
                        break
                    tag = entry[:3]
                    try:
                        length = int(entry[3:7])
                        start_pos = int(entry[7:12])
                        field_data = variable_fields_part[start_pos:start_pos+length]
                        fields.append((tag, field_data))
                    except ValueError:
                        continue
            else:
                fields = []

            # 1. AR Points 추출 (521 필드 또는 전체 텍스트 내 탐색)
            ar_point = ""
            ar_found = False
            for tag, f_data in fields:
                if tag == '521':
                    ar_match = re.search(r'AR\s*P[io]+nts?\s*[:]?\s*([\d\.]+)', f_data, re.IGNORECASE)
                    if ar_match:
                        ar_point = ar_match.group(1)
                        ar_found = True
                        break
            if not ar_found:
                ar_match = re.search(r'AR\s*P[io]+nts?\s*[:]?\s*([\d\.]+)', rec, re.IGNORECASE)
                if ar_match:
                    ar_point = ar_match.group(1)
            
            if not ar_point:
                continue

            # 2. 090 필드 추출 ($a와 $b가 모두 존재하는 필드 우선 선택)
            candidates_090 = []
            for tag, f_data in fields:
                if tag == '090':
                    subfields = re.split(r'[\x1f]', f_data)
                    s_a = ""
                    s_b = ""
                    for sub in subfields:
                        if sub.startswith('a'):
                            s_a = sub[1:].strip()
                        elif sub.startswith('b'):
                            s_b = sub[1:].strip()
                    candidates_090.append((s_a, s_b))

            if not candidates_090 and '090' in rec:
                search_target = variable_fields_part if 'variable_fields_part' in locals() else rec
                matches_090 = search_target.split('090')
                for chunk in matches_090[1:]:
                    chunk_sub = chunk[:120]
                    a_match = re.search(r'(?:[\x1f]a|a)\s*([0-9]+(?:\.[0-9]+)?)', chunk_sub)
                    b_match = re.search(r'(?:[\x1f]b|b)\s*([A-Za-z0-9\-\.]+)', chunk_sub)
                    s_a = a_match.group(1).strip() if a_match else ""
                    s_b = b_match.group(1).strip() if b_match else ""
                    if s_a or s_b:
                        candidates_090.append((s_a, s_b))

            selected_a = ""
            selected_b = ""
            for sa, sb in candidates_090:
                if sa and sb:
                    selected_a = sa
                    selected_b = sb
                    break
            if not selected_a and not selected_b and candidates_090:
                selected_a, selected_b = candidates_090[0]

            part_a = selected_a
            part_b = selected_b
            if part_b:
                clean_b = re.match(r'([A-Za-z]+\d+[A-Za-z0-9\-\.]*)', part_b)
                if clean_b:
                    part_b = clean_b.group(1)

            # 분류번호와 도서기호를 하나로 합치기
            if part_a and part_b:
                call_number = f"{part_a} {part_b}"
            else:
                call_number = part_a or part_b

            # 3. 049 필드 추출 (등록번호 여러 개 및 별치기호 처리)
            loc_reg_pairs = []
            for tag, f_data in fields:
                if tag == '049':
                    subfields = re.split(r'[\x1f]', f_data)
                    f_val = ""
                    reg_list = []
                    for sub in subfields:
                        if sub.startswith('f'):
                            f_val = sub[1:].strip()
                        elif sub.startswith('l'):
                            r_val = sub[1:].strip()
                            if r_val.startswith('DJU'):
                                reg_list.append(r_val)
                    for r in reg_list:
                        loc_reg_pairs.append((f_val, r))

            if not loc_reg_pairs:
                f_match = re.search(r'(?:[\x1f]f|f)([A-Za-z0-9\-]+)', rec)
                f_val = f_match.group(1).strip() if f_match else ""
                reg_no_matches = re.findall(r'(DJU[A-Za-z0-9\-_]+)', rec)
                for r in reg_no_matches:
                    loc_reg_pairs.append((f_val, r))

            if not loc_reg_pairs:
                reg_no_match = re.search(r'(DJU[A-Za-z0-9\-_]+)', rec)
                reg_no = reg_no_match.group(1) if reg_no_match else ""
                f_match = re.search(r'(?:[\x1f]f|f)([A-Za-z0-9\-]+)', rec)
                f_val = f_match.group(1).strip() if f_match else ""
                loc_reg_pairs.append((f_val, reg_no))

            def get_location_label(f_val):
                if f_val == 'KP': return "원-유"
                elif f_val == 'KC': return "원아"
                elif f_val == 'KE': return "원서"
                return f_val

            def clean_text(text):
                if not isinstance(text, str): return text
                return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text).strip()

            for f_val, reg_no in loc_reg_pairs:
                location_label = get_location_label(f_val)
                data_list.append({
                    "시작등록번호": clean_text(reg_no),
                    "별치기호": clean_text(location_label),
                    "청구기호": clean_text(call_number),
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
