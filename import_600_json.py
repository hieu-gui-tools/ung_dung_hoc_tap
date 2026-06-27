import os
import sys
import json
import re

# Connect to DB
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.data.database import get_session, ChuDe, Chuong, Bai, CauHoi, init_db

def load_github_dataset():
    print("Loading github dataset...")
    try:
        content = open('github_script.js', encoding='utf-8').read()
        m = re.search(r'const\s+QUESTIONS\s*=\s*(\[.*?\]);', content, re.DOTALL)
        if m:
            return json.loads(m.group(1))
    except Exception as e:
        print("Error loading github dataset:", e)
    return []

def main():
    session = get_session()
    
    # Ensure hierarchy exists
    chude_name = "thi_bang_lai_xe"
    chuong_name = "B"
    bai_name = "nam_2026"
    
    chu_de = session.query(ChuDe).filter_by(ten=chude_name).first()
    chuong = session.query(Chuong).filter_by(ten=chuong_name, chu_de_id=chu_de.id).first()
    bai = session.query(Bai).filter_by(ten=bai_name, chuong_id=chuong.id).first()
    
    # 1. Wipe existing questions in this bai
    deleted = session.query(CauHoi).filter_by(bai_id=bai.id).delete()
    print(f"Deleted {deleted} existing questions.")
    
    # 2. Load dataset
    dataset = load_github_dataset()
    print(f"Loaded {len(dataset)} reference questions from JSON.")
    
    added_count = 0
    for item in dataset:
        q_text = item.get('q', '').strip()
        img_url = item.get('img', '')
        ans_idx = item.get('ans', 1)
        tip = item.get('tip', '')
        
        # Options
        opts = ["", "", "", "", ""]
        options = item.get('opts', [])
        for i, opt in enumerate(options):
            if i < 5:
                opts[i] = opt.get('t', '').strip()
                
        # Correct answer logic
        correct_ans = chr(64 + ans_idx) if 1 <= ans_idx <= 5 else 'A'
        
        new_q = CauHoi(
            noi_dung=q_text,
            hinh_anh=img_url,
            lua_chon_a=opts[0],
            lua_chon_b=opts[1],
            lua_chon_c=opts[2],
            lua_chon_d=opts[3],
            lua_chon_e=opts[4],
            dap_an=correct_ans,
            giai_thich=tip,
            bai_id=bai.id
        )
        session.add(new_q)
        added_count += 1
        
    session.commit()
    print(f"Done! Inserted {added_count} questions.")
    
    # Verify DB
    count = session.query(CauHoi).filter_by(bai_id=bai.id).count()
    print(f"Verification: There are {count} questions in nam_2026.")

if __name__ == "__main__":
    main()
