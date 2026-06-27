import sys
import os

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from data.database import get_session, ChuDe, Chuong, Bai, CauHoi

def insert_synthetic_b1_questions():
    db = get_session()
    
    # 1. Create or get ChuDe
    chude = db.query(ChuDe).filter(ChuDe.ten == "tienganh_b1").first()
    if not chude:
        chude = ChuDe(ten="tienganh_b1", mo_ta="Các câu hỏi tiếng Anh trình độ B1")
        db.add(chude)
        db.commit()
        
    # 2. Create or get Chuong
    chuong = db.query(Chuong).filter(Chuong.ten == "grammar_vocab", Chuong.chu_de_id == chude.id).first()
    if not chuong:
        chuong = Chuong(ten="grammar_vocab", chu_de_id=chude.id)
        db.add(chuong)
        db.commit()
        
    # 3. Create or get Bai
    bai = db.query(Bai).filter(Bai.ten == "test_01", Bai.chuong_id == chuong.id).first()
    if not bai:
        bai = Bai(ten="test_01", chuong_id=chuong.id)
        db.add(bai)
        db.commit()
        
    questions = [
        {
            "noidung": "I _____ to London three times so far.",
            "a": "go",
            "b": "went",
            "c": "have been",
            "d": "was going",
            "answer": "C"
        },
        {
            "noidung": "While she _____ dinner, the phone rang.",
            "a": "cooks",
            "b": "was cooking",
            "c": "has cooked",
            "d": "is cooking",
            "answer": "B"
        },
        {
            "noidung": "If it rains tomorrow, we _____ at home.",
            "a": "stay",
            "b": "will stay",
            "c": "stayed",
            "d": "would stay",
            "answer": "B"
        },
        {
            "noidung": "You _____ smoke in the hospital. It's forbidden.",
            "a": "must",
            "b": "can",
            "c": "mustn't",
            "d": "could",
            "answer": "C"
        },
        {
            "noidung": "He is _____ than his brother.",
            "a": "the most tall",
            "b": "taller",
            "c": "more taller",
            "d": "tall",
            "answer": "B"
        },
        {
            "noidung": "I _____ live in New York.",
            "a": "used to",
            "b": "am used to",
            "c": "use to",
            "d": "did used to",
            "answer": "A"
        },
        {
            "noidung": "She asked me where I _____.",
            "a": "live",
            "b": "lived",
            "c": "do I live",
            "d": "did I live",
            "answer": "B"
        },
        {
            "noidung": "I'm really looking forward to _____ you.",
            "a": "see",
            "b": "seeing",
            "c": "saw",
            "d": "seen",
            "answer": "B"
        },
        {
            "noidung": "By the time we arrived, the film _____.",
            "a": "started",
            "b": "has started",
            "c": "had started",
            "d": "starts",
            "answer": "C"
        },
        {
            "noidung": "This is the man _____ car was stolen.",
            "a": "who",
            "b": "which",
            "c": "whose",
            "d": "that",
            "answer": "C"
        },
        {
            "noidung": "I wish I _____ more free time.",
            "a": "have",
            "b": "had",
            "c": "will have",
            "d": "can have",
            "answer": "B"
        },
        {
            "noidung": "The house _____ built in 1990.",
            "a": "is",
            "b": "was",
            "c": "has been",
            "d": "had been",
            "answer": "B"
        },
        {
            "noidung": "We have been living here _____ 2010.",
            "a": "for",
            "b": "since",
            "c": "in",
            "d": "from",
            "answer": "B"
        },
        {
            "noidung": "She is very good _____ playing the piano.",
            "a": "in",
            "b": "at",
            "c": "on",
            "d": "with",
            "answer": "B"
        },
        {
            "noidung": "Do you mind _____ the window?",
            "a": "open",
            "b": "to open",
            "c": "opening",
            "d": "opened",
            "answer": "C"
        },
        {
            "noidung": "If I _____ you, I wouldn't do that.",
            "a": "am",
            "b": "was",
            "c": "were",
            "d": "have been",
            "answer": "C"
        },
        {
            "noidung": "They will _____ the project by next week.",
            "a": "finish",
            "b": "have finished",
            "c": "be finishing",
            "d": "had finished",
            "answer": "B"
        },
        {
            "noidung": "She _____ her hair cut yesterday.",
            "a": "has",
            "b": "had",
            "c": "have",
            "d": "having",
            "answer": "B"
        },
        {
            "noidung": "I don't have _____ money left.",
            "a": "some",
            "b": "any",
            "c": "many",
            "d": "a lot",
            "answer": "B"
        },
        {
            "noidung": "He is the _____ student in the class.",
            "a": "intelligent",
            "b": "more intelligent",
            "c": "most intelligent",
            "d": "intelligentest",
            "answer": "C"
        }
    ]

    added = 0
    for q in questions:
        # Check if already exists
        exist = db.query(CauHoi).filter(CauHoi.noi_dung == q["noidung"], CauHoi.bai_id == bai.id).first()
        if not exist:
            new_q = CauHoi(
                noi_dung=q["noidung"],
                lua_chon_a=q["a"],
                lua_chon_b=q["b"],
                lua_chon_c=q["c"],
                lua_chon_d=q["d"],
                dap_an=q["answer"],
                bai_id=bai.id
            )
            db.add(new_q)
            added += 1
            
    db.commit()
    db.close()
    print(f"Added {added} synthetic B1 English questions to DB.")

if __name__ == '__main__':
    insert_synthetic_b1_questions()
