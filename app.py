import re
import pandas as pd
import streamlit as st
from PIL import Image

# 웹페이지 기본 설정
st.set_page_config(page_title="MARC AR 포인트 추출기", page_icon="📚", layout="centered")

# 로고 이미지 불러오기 (logo.png 파일이 있을 때만 표시)
try:
    img = Image.open("logo.png")
    st.image(img, width=150)
except Exception:
    pass 

st.title("📚 코라스 MARC AR 포인트 추출기")
st.write("코라스(KOLAS)에서 추출한 마크(.TXT) 파일을 업로드하면 등록번호, 청구기호, AR 포인트를 자동으로 정리해 줍니다.")

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
            # AR 포인트나 관련 키워드가 포함된 레코드 처리
            if 'AR' in rec or 'Pi' in rec or 'DJU' in rec or '090' in rec:
                ar_match = re.search(r'AR\s*P[io]+nts?\s*[:]?\s*([\d\.]+)', rec, re.IGNORECASE)
                
                if ar_match:
                    ar_point = ar_match.group(1)
                    
                    # 1. 등록번호 추출 (DJU...)
                    reg_no_match = re.search(r'(DJU[A-Za-z0-9\-_]+)', rec)
                    reg_no = reg_no_match.group(1) if reg_no_match else ""
                    
                    # 2. 청구기호 추출 (090 필드 및 a, b 파싱)
                    call_number = ""
                    # 090 필드 부분 찾기 (090 뒤의 내용 추출)
                    field_090_match = re.search(r'090\s*(.*?)(?=\n|\x1e|\d{3}\s|$)', rec, re.DOTALL)
                    if field_090_match:
                        f090_text = field_090_match.group(1)
                        # a (분류번호) 와 b (도서기호) 추출 (유니코드 서브필드 구분자  또는 제어문자 대응)
                        sub_a_match = re.search(r'(?:[\x1f]a|a)([^\x1f\n\t]+)', f090_text)
                        sub_b_match = re.search(r'(?:[\x1f]b|b)([^\x1f\n\t]+)', f090_text)
                        
                        part_a = sub_a_match.group(1).strip() if sub_a_match else ""
                        part_b = sub_b_match.group(1).strip() if sub_b_match else ""
                        
                        # 분류번호와 도서기호를 조합 (예: 843 M56t)
                        if part_a and part_b:
                            call_number = f"{part_a} {part_b}"
                        elif part_a:
                            call_number = part_a
                        elif part_b:
                            call_number = part_b
                    
                    # 만약 위 정규식으로 090을 못 찾았을 경우를 대비한 유연한 대안 탐색
                    if not call_number:
                        sub_a_alt = re.search(r'[\x1f]a([^\x1f\n]+)', rec)
                        sub_b_alt = re.search(r'[\x1f]b([^\x1f\n]+)', rec)
                        if sub_a_alt:
                            p1 = sub_a_alt.group(1).strip()
                            p2 = sub_b_alt.group(1).strip() if sub_b_alt else ""
                            call_number = f"{p1} {p2}".strip()

                    data_list.append({
                        "시작등록번호": reg_no,
                        "청구기호": call_number,
                        "AR_Points": ar_point
                    })
                    
        df = pd.DataFrame(data_list).drop_duplicates()
        
        if not df.empty:
            st.success(f"총 {len(df)}개의 데이터를 성공적으로 추출했습니다!")
            st.dataframe(df, use_container_width=True)
            
            excel_file = 'AR_Points_With_CallNumber.xlsx'
            df.to_excel(excel_file, index=False)
            
            with open(excel_file, "rb") as f:
                st.download_button(
                    label="📥 엑셀 파일 다운로드하기",
                    data=f,
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("추출된 데이터가 없습니다. 파일 내용을 다시 한 번 확인해 주세요.")
