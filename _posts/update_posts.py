import os
import re

def process_all_features():
    # 1. 스크립트 파일이 위치한 폴더를 기준으로 경로 설정
    base_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = base_dir
    target_dir = os.path.join(base_dir, '_change')
    
    # 2. _change 폴더 생성
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    # 3. 소스 폴더에 있는 모든 .md 파일 목록 가져오기
    md_files = [f for f in os.listdir(source_dir) if f.endswith('.md')]
    
    count = 0
    for filename in md_files:
        filepath = os.path.join(source_dir, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 4. 정규표현식을 사용해 Front Matter(설정 영역)와 본문을 3등분
        parts = re.split(r'^-{3,}\s*$', content, maxsplit=2, flags=re.MULTILINE)
        
        if len(parts) < 3:
            continue
            
        front_matter = parts[1]
        body = parts[2]
        
        # 5. 본문 치환 규칙: 인사말 변경
        body = body.replace("라보엠", "**한스**")
        
        # 🌟 본문 치환 규칙: 문단 시작 번호를 마크다운 헤더(##)로 변환 🌟
        # ^\s* : 줄의 시작과 선택적 공백
        # (\d+) : 1개 이상의 숫자(그룹 지정)
        # \.\s : 마침표와 공백 1칸
        # flags=re.MULTILINE : 모든 줄의 시작점을 개별적으로 검사
        body = re.sub(r'^\s*(\d+)\.\s', r'## \1. ', body, flags=re.MULTILINE)
        
        # 설정 영역 분석
        lines = front_matter.strip().split('\n')
        new_lines = []
        
        artist_name = ""
        has_tags = False
        categories_idx = -1
        
        for line in lines:
            clean_line = line.rstrip()
            
            # 규칙 1: excerpt 주석 처리
            if clean_line.startswith('excerpt:'):
                clean_line = '# ' + clean_line
                
            # 규칙 2: 기존 태그 존재 여부 확인
            if clean_line.startswith('tags:'):
                has_tags = True
                
            # 규칙 3: 타이틀에서 괄호 안의 작가/가수 이름 추출 및 띄어쓰기 변환
            if clean_line.startswith('title:'):
                raw_title = clean_line.replace('title:', '').strip().strip('\'"')
                match = re.search(r'\[(.*?)\]\s*(.*)', raw_title)
                if match:
                    bracket_word = match.group(1).strip()
                    rest_title = match.group(2).strip()
                    
                    if bracket_word == "지금이노래":
                        if rest_title:
                            artist_name = rest_title.split()[0]
                    else:
                        artist_name = bracket_word
                    
                    # 띄어쓰기를 언더바(_)로 변환
                    if artist_name:
                        artist_name = artist_name.replace(' ', '_')
                        
            # 규칙 4: 카테고리 대분류 추가 및 완벽한 중복 방지
            if clean_line.startswith('categories:'):
                categories_idx = len(new_lines)
                cat_value = clean_line.replace('categories:', '').strip()
                
                if cat_value:
                    words = cat_value.split()
                    
                    if len(words) == 1:
                        main_cat_raw = cat_value.split('.')[0]
                        main_cat_title = main_cat_raw.capitalize()
                        
                        if cat_value.lower() != main_cat_title.lower():
                            clean_line = f"categories: {main_cat_title} {cat_value}"
                        
            new_lines.append(clean_line)
            
        # 규칙 5: 태그가 없었고 이름이 추출되었다면 카테고리 아래에 태그 삽입
        if not has_tags and artist_name and categories_idx != -1:
            new_lines.insert(categories_idx + 1, f"tags: {artist_name}")
            
        # 6. 수정 내용 병합
        new_front_matter = '\n'.join(new_lines)
        new_content = f"---\n{new_front_matter}\n---{body}"
        
        # 7. 변경된 파일 저장
        target_filepath = os.path.join(target_dir, filename)
        with open(target_filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        count += 1
        
    print(f"작업 완료! 총 {count}개의 포스팅 파일이 성공적으로 수정되어 '_change' 폴더에 저장되었습니다.")

if __name__ == "__main__":
    process_all_features()