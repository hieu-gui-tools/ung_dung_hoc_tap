import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.data.database import get_session, CauHoi

def main():
    session = get_session()
    qs = session.query(CauHoi).all()
    count = 0
    base = os.path.dirname(os.path.abspath(__file__))
    
    for q in qs:
        if q.hinh_anh and q.hinh_anh.startswith(base):
            q.hinh_anh = os.path.relpath(q.hinh_anh, base).replace('\\', '/')
            count += 1
            
    session.commit()
    print(f'Updated {count} paths to relative')

if __name__ == "__main__":
    main()
