import re

def parse_marc_record(record_text):
    """
    단일 MARC 레코드 텍스트에서 049(별치기호 등)와 090(청구기호) 필드를 안전하게 파싱하는 함수
    """
    shelf_location = ""  # 별치기호 (049 필드 등에서 추출)
    call_number = ""     # 청구기호 (090 필드)
    
    # 레코드를 줄 단위 또는 필드 단위로 분리 (MARC Dump 또는 일반 텍스트 반출 형식 대응)
    lines = record_text.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 049 필드 처리 (예: 049 __ $a... $f별치기호)
        if line.startswith("049"):
            # 서브필드 $f 또는 별치기호 매핑 추출 정규식
            # 시스템에 따라 $f 혹은 특정 위치에 별치 코드가 위치할 수 있음
            f_match = re.search(r'\$f\s*([^\$\t]+)', line)
                if f_match:
                shelf_location = f_match.group(1).strip()
            # 만약 구분자가 다른 형태($가 아닌 기호 등)라면 추가 정제 필요
            
        # 090 필드 처리 (청구기호: 분류번호 $a + 도서기호 $b 등)
        elif line.startswith("090"):
            # 020(ISBN) 등 다른 필드가 090으로 오인되지 않도록 시작 문자열 엄격 확인
            # 서브필드 $a와 $b 추출
            sub_a = re.search(r'\$a\s*([^\$\t]+)', line)
            sub_b = re.search(r'\$b\s*([^\$\t]+)', line)
            
            a_val = sub_a.group(1).strip() if sub_a else ""
            b_val = sub_b.group(1).strip() if sub_b else ""
            
            # $a와 $b를 조합하여 청구기호 완성
            if a_val and b_val:
                call_number = f"{a_val} {b_val}"
            elif a_val:
                call_number = a_val
            elif b_val:
                call_number = b_val
                
    return shelf_location, call_number


def process_marc_file(file_path):
    """
    마크 반출 파일을 읽어와 레코드별로 별치기호와 청구기호를 추출하는 메인 함수
    """
    results = []
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    # 레코드 구분자(예: 레코드 단위 분할이 필요한 경우 기호에 맞춰 조정)
    # 코라스 등 일반 텍스트 반출 파일의 경우 빈 줄이나 특정 패턴으로 분리됨
    records = content.split('\n\n') # 파일 형식에 따라 '\x1d' 또는 '\n\n' 등 조정 필요
    
    for idx, record in enumerate(records):
        if not record.strip():
            continue
            
        shelf, call = parse_marc_record(record)
        
        # 데이터가 정상적으로 잡히지 않을 경우를 대비한 2차 정규식 보완 탐색
        if not call:
            # 090 필드가 변형되어 들어온 경우를 위한 백업 로직
            match_090 = re.search(r'090.*?\$a([^\$]+)(?:\$b([^\$]+))?', record)
            if match_090:
                part1 = match_090.group(1).strip() if match_090.group(1) else ""
                part2 = match_090.group(2).strip() if match_090.group(2) else ""
                call = f"{part1} {part2}".strip()

        results.append({
            'index': idx + 1,
            'shelf_location': shelf,
            'call_number': call
        })
        
    return results

# 사용 예시 (스트림릿이나 로컬 실행 시 파일 경로 입력)
# parsed_data = process_marc_file('your_marc_file.mrc')
