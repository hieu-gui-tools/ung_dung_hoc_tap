import os
import sys
import re
import requests
from bs4 import BeautifulSoup
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.data.database import get_session, ChuDe, Chuong, Bai, CauHoi

def extract_links(url):
    print(f"Fetching category: {url}")
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    main = soup.find('main') or soup.find(id='content') or soup
    
    links = []
    for a in main.find_all('a', href=True):
        href = a['href']
        text = a.text.strip()
        # English tests
        if text and 'tieng-anh' in href and 'kien-thuc' not in href:
            if (text, href) not in links:
                links.append((text, href))
    return links

def parse_question_text(raw_text):
    # Splits the raw text of a P tag into Question and Options
    # Format typically:
    # Câu 1: blah blah
    # A. opt1
    # B. opt2
    # C. opt3
    # D. opt4
    
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    q_text = ""
    opts = []
    
    for line in lines:
        if re.match(r'^[A-D][\.\:]\s+', line, re.IGNORECASE):
            opts.append(line)
        else:
            q_text += line + "\n"
            
    q_text = q_text.strip()
    
    # Clean up the prefix "Câu X:" or "Question X:"
    q_text = re.sub(r'^(Câu|Question)\s*\d+[\.\:]\s*', '', q_text, flags=re.IGNORECASE).strip()
    
    # If options didn't split well, try splitting by A., B., C., D. inline
    if len(opts) == 0:
        match = re.search(r'(.*?)(A[\.\:].*?)(B[\.\:].*?)(C[\.\:].*?)(D[\.\:].*?)$', q_text, flags=re.IGNORECASE|re.DOTALL)
        if match:
            q_text = match.group(1).strip()
            opts = [match.group(2).strip(), match.group(3).strip(), match.group(4).strip(), match.group(5).strip()]
            
    # Remove A., B., C., D. prefix from options
    cleaned_opts = []
    for opt in opts:
        cleaned = re.sub(r'^[A-D][\.\:]\s*', '', opt, flags=re.IGNORECASE).strip()
        cleaned_opts.append(cleaned)
        
    return q_text, cleaned_opts

def scrape_test(url):
    print(f"Scraping test: {url}")
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    main = soup.find('main') or soup.find(id='content') or soup
    
    questions = []
    for p in main.find_all('p'):
        text = p.get_text(separator='\n').strip()
        if re.match(r'^(Câu|Question)\s*\d+[\.\:]', text, re.IGNORECASE) or (len(text) > 5 and text[0].isdigit() and text[1] in '.:'):
            q_text, opts = parse_question_text(text)
            if q_text and len(opts) >= 2:
                # pad to 4 options if necessary
                while len(opts) < 4:
                    opts.append("")
                questions.append({
                    "noi_dung": q_text,
                    "lua_chon_a": opts[0],
                    "lua_chon_b": opts[1],
                    "lua_chon_c": opts[2],
                    "lua_chon_d": opts[3],
                    "dap_an": "A", # Defaulting to A as answers are not provided
                    "giai_thich": "Chưa có giải thích.",
                    "hinh_anh": ""
                })
    return questions

def main():
    session = get_session()
    
    # Ensure Hierarchy exists
    chude_name = "dethitracnghiem.vn"
    chuong_name = "tieng_anh"
    
    chude = session.query(ChuDe).filter_by(ten=chude_name).first()
    if not chude:
        chude = ChuDe(ten=chude_name, mo_ta="Nguồn từ dethitracnghiem.vn")
        session.add(chude)
        session.commit()
        
    chuong = session.query(Chuong).filter_by(ten=chuong_name, chu_de_id=chude.id).first()
    if not chuong:
        chuong = Chuong(ten=chuong_name, chu_de_id=chude.id)
        session.add(chuong)
        session.commit()
        
    urls_to_crawl = [
        "https://dethitracnghiem.vn/kien-thuc/tieng-anh/tu-vung/",
        "https://dethitracnghiem.vn/kien-thuc/tieng-anh/ngu-phap/"
    ]
    
    all_links = []
    for cat_url in urls_to_crawl:
        links = extract_links(cat_url)
        all_links.extend(links)
        
    # Deduplicate links by URL
    seen_urls = set()
    unique_links = []
    for title, url in all_links:
        if url not in seen_urls:
            seen_urls.add(url)
            unique_links.append((title, url))
            
    print(f"Found {len(unique_links)} unique tests to scrape.")
    
    total_q = 0
    for title, url in unique_links:
        questions = scrape_test(url)
        if questions:
            print(f" -> Found {len(questions)} questions")
            # Create Bai
            # Format title to be safer for name (keep it descriptive)
            bai_name = title
            bai = session.query(Bai).filter_by(ten=bai_name, chuong_id=chuong.id).first()
            if not bai:
                bai = Bai(ten=bai_name, chuong_id=chuong.id)
                session.add(bai)
                session.commit()
            
            # Remove old questions if overwriting
            session.query(CauHoi).filter_by(bai_id=bai.id).delete()
            session.commit()
            
            for q in questions:
                cau_hoi = CauHoi(
                    bai_id=bai.id,
                    noi_dung=q["noi_dung"],
                    hinh_anh=q["hinh_anh"],
                    lua_chon_a=q["lua_chon_a"],
                    lua_chon_b=q["lua_chon_b"],
                    lua_chon_c=q["lua_chon_c"],
                    lua_chon_d=q["lua_chon_d"],
                    dap_an=q["dap_an"],
                    giai_thich=q["giai_thich"]
                )
                session.add(cau_hoi)
            session.commit()
            total_q += len(questions)
        else:
            print(" -> 0 questions found.")
            
    print(f"Scraping complete! Added {total_q} questions across tests.")
    
if __name__ == "__main__":
    main()
