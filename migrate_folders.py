import os
import shutil
import re
import html
from datetime import datetime
from bs4 import BeautifulSoup

# 설정 경로
SOURCE_DIR = "./tistory_backup_posts"  # 티스토리 백업 폴더
TARGET_POSTS_DIR = "./_posts"          # Jekyll _posts 폴더
TARGET_IMG_DIR = "./assets/images"     # Jekyll 이미지 폴더

def clean_and_convert_html(body_tag, post_id):
    if not body_tag:
        return ""

    # 1. H2 태그 추출 후 마커로 치환
    for h2 in body_tag.find_all('h2'):
        h2_text = h2.get_text(strip=True)
        h2.replace_with(f"\n\n__H2_MARKER__{h2_text}__H2_END__\n\n")

    # 2. 유튜브 데이터(figure, iframe) 추출 후 마커로 치환
    for fig in body_tag.find_all('figure', attrs={'data-video-host': 'youtube'}):
        url = fig.get('data-video-url', '')
        match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11})', url)
        if match:
            fig.replace_with(f"\n\n__YOUTUBE_MARKER__{match.group(1)}__YOUTUBE_END__\n\n")
        else:
            fig.decompose()
            
    for iframe in body_tag.find_all('iframe'):
        src = iframe.get('src', '')
        match = re.search(r'(?:v=|embed/|youtu\.be/)([0-9A-Za-z_-]{11})', src)
        if match:
            iframe.replace_with(f"\n\n__YOUTUBE_MARKER__{match.group(1)}__YOUTUBE_END__\n\n")
        else:
            iframe.decompose()

    # 3. 이미지 태그 경로 수정 후 마커로 치환
    for img in body_tag.find_all('img'):
        src = img.get('src', '')
        filename = os.path.basename(src)
        if filename:
            new_src = f"/assets/images/{post_id}/{filename}"
            alt = img.get('alt', '')
            img.replace_with(f"\n\n__IMG_MARKER__{new_src}||{alt}__IMG_END__\n\n")
        else:
            img.decompose()
            
    # 4. 외부 링크 추출 후 마커로 치환 (오픈그래프용)
    for a_tag in body_tag.find_all('a'):
        href = a_tag.get('href', '')
        
        # 안전장치: 링크 안에 이미지가 포함된 경우(티스토리 사진 라이트박스 등)는 변환 제외
        if '__IMG_MARKER__' in str(a_tag):
            a_tag.unwrap()
            continue
            
        # 외부 웹사이트 주소인 경우 오픈그래프 마커로 치환
        if href.startswith('http'):
            a_tag.replace_with(f"\n\n__LINK_MARKER__{href}__LINK_END__\n\n")
        else:
            a_tag.unwrap()
            
    # 5. 본문 내 숨겨진 스크립트나 스타일 태그 완전히 제거
    for hidden in body_tag.find_all(['script', 'style', 'head', 'meta', 'link']):
        hidden.decompose()

    # 블록 요소들의 문단 구분을 위해 태그 끝에 강제 개행 추가
    for tag in body_tag.find_all(['p', 'div', 'br', 'li', 'tr', 'h1', 'h3', 'h5', 'h6']):
        tag.append("\n")

    # 남은 모든 HTML 태그를 벗겨내어 텍스트만 남김 (unwrap)
    while True:
        tag = body_tag.find(True)
        if not tag:
            break
        tag.unwrap()

    # HTML 특수 기호를 원래 텍스트로 복원
    raw_text = html.unescape(body_tag.decode_contents())

    # 추출된 텍스트 라인별 스페이스 2칸 및 마커 복원 작업
    lines = raw_text.split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            processed_lines.append("") 
            continue
        
        # H2 마커 복원
        if '__H2_MARKER__' in line:
            line = re.sub(r'__H2_MARKER__(.*?)__H2_END__', r'# \1', line)
            processed_lines.append(line)
            continue
        
        # 유튜브 마커 복원
        if '__YOUTUBE_MARKER__' in line:
            line = re.sub(r'__YOUTUBE_MARKER__(.*?)__YOUTUBE_END__', r'{% include video id="\1" provider="youtube" %}', line)
            processed_lines.append(line)
            continue
        
        # 이미지 마커 복원
        if '__IMG_MARKER__' in line:
            line = re.sub(r'__IMG_MARKER__(.*?)\|\|(.*?)__IMG_END__', r'<img src="\1" alt="\2">', line)
            processed_lines.append(line)
            continue
            
        # 🌟 링크 마커를 오픈그래프 리퀴드 카드로 복원 🌟
        if '__LINK_MARKER__' in line:
            line = re.sub(r'__LINK_MARKER__(.*?)__LINK_END__', r'{% include auto-link.html url="\1" %}', line)
            processed_lines.append(line)
            continue

        # 일반 텍스트 라인의 끝에는 스페이스 2칸을 강제로 추가
        processed_lines.append(line + "  ")

    # 최종 텍스트 병합 및 연속된 빈 줄 최소화
    final_output = "\n".join(processed_lines)
    final_output = re.sub(r'\n{3,}', '\n\n', final_output)
    
    return final_output.strip()

def advanced_migrate():
    if not os.path.exists(SOURCE_DIR):
        print(f"오류: {SOURCE_DIR} 폴더를 찾을 수 없습니다.")
        return

    os.makedirs(TARGET_POSTS_DIR, exist_ok=True)

    for post_folder in os.listdir(SOURCE_DIR):
        folder_path = os.path.join(SOURCE_DIR, post_folder)
        
        if os.path.isdir(folder_path):
            post_id = post_folder
            
            src_img_folder = os.path.join(folder_path, "img")
            dest_img_folder = os.path.join(TARGET_IMG_DIR, post_id)
            
            first_image_path = ""
            if os.path.exists(src_img_folder):
                os.makedirs(dest_img_folder, exist_ok=True)
                img_files = sorted(os.listdir(src_img_folder))
                for img_file in img_files:
                    if img_file.startswith('.'):
                        continue
                    shutil.copy(
                        os.path.join(src_img_folder, img_file),
                        os.path.join(dest_img_folder, img_file)
                    )
                valid_imgs = [f for f in img_files if not f.startswith('.')]
                if valid_imgs:
                    first_image_path = f"/assets/images/{post_id}/{valid_imgs[0]}"

            for file_name in os.listdir(folder_path):
                if file_name.endswith(".html") or file_name.endswith(".md"):
                    src_file = os.path.join(folder_path, file_name)
                    
                    with open(src_file, "r", encoding="utf-8") as f:
                        raw_html = f.read()
                    
                    soup = BeautifulSoup(raw_html, 'html.parser')
                    
                    title_tag = soup.find('title')
                    post_title = title_tag.text.strip() if title_tag else f"Post {post_id}"
                    
                    category_tag = soup.find('p', class_='category')
                    post_category = category_tag.text.strip() if category_tag else ""
                    if category_tag:
                        category_tag.decompose()

                    tags_tag = soup.find(class_='tags')
                    post_tags = []
                    if tags_tag:
                        tags_text = tags_tag.text.strip()
                        if tags_text:
                            raw_tags = re.findall(r'#([^\s,]+)', tags_text)
                            post_tags = raw_tags[:2]
                        tags_tag.decompose()

                    date_tag = soup.find('p', class_='date')
                    extracted_date_str = date_tag.text.strip() if date_tag else ""
                    if date_tag:
                        date_tag.decompose()

                    file_date_prefix = datetime.now().strftime('%Y-%m-%d')
                    formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S +0900')

                    if extracted_date_str:
                        try:
                            parsed_dt = datetime.strptime(extracted_date_str, "%Y-%m-%d %H:%M:%S")
                            file_date_prefix = parsed_dt.strftime('%Y-%m-%d')
                            formatted_date = parsed_dt.strftime('%Y-%m-%d %H:%M:%S +0900')
                        except ValueError:
                            pass

                    h2_title_tag = soup.find('h2', class_='title-article')
                    if h2_title_tag:
                        h2_title_tag.decompose()

                    body_tag = soup.find('body')
                    post_excerpt = ""
                    if body_tag:
                        plain_text = body_tag.get_text(separator=' ', strip=True)
                        post_excerpt = plain_text[:150].replace('"', "'").replace('\n', ' ') + "..."
                        post_content = clean_and_convert_html(body_tag, post_id)
                    else:
                        post_content = raw_html

                    front_matter = f"""---
layout: single
title: "{post_title}"
date: {formatted_date}
permalink: /{post_id}/
"""
                    if post_excerpt:
                        front_matter += f'excerpt: "{post_excerpt}"\n'

                    if post_category:
                        front_matter += f"categories: {post_category}\n"

                    if post_tags:
                        tags_str = " ".join(post_tags)
                        front_matter += f"tags: {tags_str}\n"

                    if first_image_path:
                        front_matter += f"""header:
  overlay_image: {first_image_path}
teaser: {first_image_path}
"""
                    front_matter += "---\n\n"

                    final_markdown_content = front_matter + post_content

                    new_file_name = f"{file_date_prefix}-{post_id}.md"
                    dest_file = os.path.join(TARGET_POSTS_DIR, new_file_name)
                    
                    with open(dest_file, "w", encoding="utf-8") as f:
                        f.write(final_markdown_content)
                        
                    print(f"정밀 변환 완료: {new_file_name}")

if __name__ == "__main__":
    advanced_migrate()