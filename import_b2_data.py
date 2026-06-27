import os
import sys
import json
import requests
from bs4 import BeautifulSoup
import re

# Connect to DB
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.data.database import get_session, ChuDe, Chuong, Bai, CauHoi, init_db

def load_github_dataset():
    print("Loading github dataset...")
    try:
        content = open('github_script.js', encoding='utf-8').read()
        # Extract JSON array
        m = re.search(r'const\s+QUESTIONS\s*=\s*(\[.*?\]);', content, re.DOTALL)
        if m:
            return json.loads(m.group(1))
    except Exception as e:
        print("Error loading github dataset:", e)
    return []

def get_answer_from_dataset(dataset, question_text, options_text):
    # Normalize question text
    q_norm = question_text.strip().lower().replace('câu hỏi:', '').replace('câu hỏi', '')
    q_norm = re.sub(r'^\s*\d+\s*:\s*', '', q_norm).strip()
    
    for item in dataset:
        item_q_norm = item.get('q', '').strip().lower()
        if q_norm in item_q_norm or item_q_norm in q_norm:
            ans_idx = item.get('ans') # 1-based index
            if ans_idx:
                return chr(64 + ans_idx) # 1 -> A, 2 -> B, ...
    return 'A' # Default fallback

def main():
    session = get_session()
    
    # Ensure hierarchy exists
    chude_name = "thi_bang_lai_xe"
    chuong_name = "B"
    bai_name = "nam_2026"
    
    chu_de = session.query(ChuDe).filter_by(ten=chude_name).first()
    if not chu_de:
        chu_de = ChuDe(ten=chude_name)
        session.add(chu_de)
        session.commit()
        
    chuong = session.query(Chuong).filter_by(ten=chuong_name, chu_de_id=chu_de.id).first()
    if not chuong:
        chuong = Chuong(ten=chuong_name, chu_de_id=chu_de.id)
        session.add(chuong)
        session.commit()
        
    bai = session.query(Bai).filter_by(ten=bai_name, chuong_id=chuong.id).first()
    if not bai:
        bai = Bai(ten=bai_name, chuong_id=chuong.id)
        session.add(bai)
        session.commit()
        
    dataset = load_github_dataset()
    print(f"Loaded {len(dataset)} reference questions.")
    
    # 1. Get all test links
    hub_url = 'https://dethitracnghiem.vn/bang-lai-xe-o-to-hang-b/'
    try:
        r = requests.get(hub_url, timeout=10)
    except Exception as e:
        print("Error getting hub:", e)
        return
        
    soup = BeautifulSoup(r.text, 'html.parser')
    links = set()
    for a in soup.find_all('a', href=True):
        if 'de-thi-bo-luat-moi-lai-xe-oto-hang-b-de' in a['href']:
            links.add(a['href'])
            
    print(f"Found {len(links)} test links to scrape.")
    
    existing_questions = set()
    # load existing from db to avoid duplicates
    for q in session.query(CauHoi).filter_by(bai_id=bai.id).all():
        existing_questions.add(q.noi_dung.strip())
        
    added_count = 0
    
    for link in links:
        print(f"Scraping {link}")
        try:
            r = requests.get(link, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.find_all('div', class_='iaeb-item')
            for item in items:
                q_div = item.find('div', class_='iaeb-quiz')
                if not q_div: continue
                
                # Question text
                q_text = q_div.text.strip()
                # Clean up "Câu hỏi 1:" prefix
                q_text = re.sub(r'^Câu hỏi\s*\d+\s*:\s*', '', q_text).strip()
                
                if q_text in existing_questions:
                    continue
                    
                # Extract image
                img_url = ""
                img_tag = q_div.find('img')
                if not img_tag:
                    img_tag = item.find('img')
                if img_tag and img_tag.has_attr('src'):
                    img_url = img_tag['src']
                    
                # Options
                opts = []
                ans_ul = item.find('div', class_='iaeb-answer')
                if ans_ul:
                    for li in ans_ul.find_all('li'):
                        # typical text looks like: A. Phần mặt đường...
                        # we only want the text inside the div or next to the span
                        opt_div = li.find('div')
                        if opt_div:
                            opts.append(opt_div.text.strip())
                        else:
                            # fallback if structure differs
                            t = li.text.strip()
                            t = re.sub(r'^[A-E]\.', '', t).strip()
                            opts.append(t)
                            
                # Fill missing options up to 5
                while len(opts) < 5:
                    opts.append("")
                    
                # Get Correct Answer from Dataset
                correct_ans = get_answer_from_dataset(dataset, q_text, opts)
                
                # Insert to DB
                new_q = CauHoi(
                    noi_dung=q_text,
                    hinh_anh=img_url,
                    lua_chon_a=opts[0] if len(opts) > 0 else "",
                    lua_chon_b=opts[1] if len(opts) > 1 else "",
                    lua_chon_c=opts[2] if len(opts) > 2 else "",
                    lua_chon_d=opts[3] if len(opts) > 3 else "",
                    lua_chon_e=opts[4] if len(opts) > 4 else "",
                    dap_an=correct_ans,
                    giai_thich="",
                    bai_id=bai.id
                )
                session.add(new_q)
                existing_questions.add(q_text)
                added_count += 1
                
            session.commit()
        except Exception as e:
            print(f"Error scraping {link}: {e}")
            session.rollback()
            
    print(f"Done! Added {added_count} unique questions.")

if __name__ == "__main__":
    main()
