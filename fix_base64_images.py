import os
import sys
import base64
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.data.database import get_session, Bai, CauHoi

def main():
    session = get_session()
    
    bai = session.query(Bai).filter_by(ten="nam_2026").first()
    if not bai:
        print("Bai not found")
        return
        
    questions = session.query(CauHoi).filter_by(bai_id=bai.id).all()
    print(f"Checking {len(questions)} questions for base64 images...")
    
    img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "b2_images")
    os.makedirs(img_dir, exist_ok=True)
    
    fixed_count = 0
    for q in questions:
        if q.hinh_anh and q.hinh_anh.startswith("data:image"):
            try:
                # Format: data:image/jpeg;base64,/9j/4AAQ...
                header, encoded = q.hinh_anh.split(",", 1)
                ext = "jpg"
                if "png" in header: ext = "png"
                
                img_data = base64.b64decode(encoded)
                filename = f"q_{q.id}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(img_dir, filename)
                
                with open(filepath, "wb") as f:
                    f.write(img_data)
                    
                # Update DB to use absolute path or relative path
                q.hinh_anh = filepath
                fixed_count += 1
            except Exception as e:
                print(f"Error decoding image for question {q.id}: {e}")
                
    session.commit()
    print(f"Fixed {fixed_count} base64 images.")
    
if __name__ == "__main__":
    main()
