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
    pass # 로고 파일이 없어도 에러 없이 그냥 넘어갑니다

st.title("📚 코라스 MARC AR 포인트 추출기")
st.write("코라스(KOLAS)에서 추출한 마크(.TXT) 파일을 업로드하면 AR 포인트와 등록번호를 자동으로 정리해 줍니다.")

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
            if 'AR' in rec or 'Pi' in rec or 'DJU' in rec:
                ar_match = re.search(r'AR\s*P[io]+nts?\s*[:]?\s*([\d\.]+)', rec, re.IGNORECASE)
                
                if ar_match:
                    ar_point = ar_match.group(1)
                    reg_no_match = re.search(r'(DJU[A-Za-z0-9\-_]+)', rec)
                    reg_no = reg_no_match.group(1) if reg_no_match else ""
                    
                    data_list.append({
                        "시작등록번호": reg_no,
                        "AR_Points": ar_point
                    })
                    
        df = pd.DataFrame(data_list).drop_duplicates()
        
        if not df.empty:
            st.success(f"총 {len(df)}개의 데이터를 성공적으로 추출했습니다!")
            st.dataframe(df, use_container_width=True)
            
            excel_file = 'AR_Points_Original_Order.xlsx'
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
