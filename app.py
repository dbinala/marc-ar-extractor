def parse_marc_record(record_text):
    """
    단일 MARC 레코드 텍스트에서 049(별치기호 등)와 090(청구기호) 필드를 안전하게 파싱하는 함수
    """
    shelf_location = ""  # 별치기호 (049 필드 등에서 추출)
    call_number = ""     # 청구기호 (090 필드)
    
    lines = record_text.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 049 필드 처리
        if line.startswith("049"):
            f_match = re.search(r'\$f\s*([^\$\t]+)', line)
            if f_match:
                shelf_location = f_match.group(1).strip()
            
        # 090 필드 처리
        elif line.startswith("090"):
            sub_a = re.search(r'\$a\s*([^\$\t]+)', line)
            sub_b = re.search(r'\$b\s*([^\$\t]+)', line)
            
            a_val = sub_a.group(1).strip() if sub_a else ""
            b_val = sub_b.group(1).strip() if sub_b else ""
            
            if a_val and b_val:
                call_number = f"{a_val} {b_val}"
            elif a_val:
                call_number = a_val
            elif b_val:
                call_number = b_val
                
    return shelf_location, call_number
