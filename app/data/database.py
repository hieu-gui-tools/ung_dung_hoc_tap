"""
app/data/database.py — SQLAlchemy models & helpers
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, Float, Boolean, ForeignKey, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

import sys
def get_db_path():
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(app_dir, "hoctap.db")

engine = None
Session = None

def init_db():
    global engine, Session
    db_path = get_db_path()
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    
    with engine.connect() as conn:
        # ── migrations ───────────────────────────────────────────────
        _try_alter(conn, "ALTER TABLE cau_hoi ADD COLUMN danh_dau BOOLEAN DEFAULT 0")
        _try_alter(conn, "ALTER TABLE cau_hoi ADD COLUMN lua_chon_e TEXT DEFAULT ''")
        _try_alter(conn, "ALTER TABLE cau_hoi ADD COLUMN hinh_anh TEXT DEFAULT ''")
        # Thêm cột bản dịch cho Audio
        _try_alter(conn, "ALTER TABLE audio ADD COLUMN ban_dich TEXT DEFAULT ''")
        conn.commit()

def _try_alter(conn, sql: str):
    try:
        conn.execute(text(sql))
    except Exception:
        pass

def get_session():
    if Session is None:
        init_db()
    return Session()


# ─── MODELS ───────────────────────────────────────────────────────────────────

class ChuDe(Base):
    __tablename__ = "chu_de"
    id   = Column(Integer, primary_key=True, autoincrement=True)
    ten  = Column(String(200), nullable=False)
    mo_ta = Column(Text, default="")
    tao_luc = Column(DateTime, default=datetime.now)
    chapters = relationship("Chuong", back_populates="chu_de", cascade="all, delete-orphan")
    nhat_kis = relationship("NhatKi", back_populates="chu_de", cascade="all, delete-orphan")


class Chuong(Base):
    __tablename__ = "chuong"
    id       = Column(Integer, primary_key=True, autoincrement=True)
    ten      = Column(String(200), nullable=False)
    chu_de_id = Column(Integer, ForeignKey("chu_de.id"))
    tao_luc  = Column(DateTime, default=datetime.now)
    chu_de   = relationship("ChuDe", back_populates="chapters")
    bais     = relationship("Bai", back_populates="chuong", cascade="all, delete-orphan")
    nhat_kis = relationship("NhatKi", back_populates="chuong", cascade="all, delete-orphan")


class Bai(Base):
    __tablename__ = "bai"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    ten       = Column(String(200), nullable=False)
    chuong_id = Column(Integer, ForeignKey("chuong.id"))
    tao_luc   = Column(DateTime, default=datetime.now)
    chuong    = relationship("Chuong", back_populates="bais")
    audios    = relationship("Audio", back_populates="bai", cascade="all, delete-orphan")
    videos    = relationship("Video", back_populates="bai", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="bai", cascade="all, delete-orphan")
    cau_hois  = relationship("CauHoi", back_populates="bai", cascade="all, delete-orphan")
    nhat_kis  = relationship("NhatKi", back_populates="bai", cascade="all, delete-orphan")
    van_ban_luyen_nhos = relationship("VanBanLuyenNho", back_populates="bai", cascade="all, delete-orphan")


class Audio(Base):
    __tablename__ = "audio"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    ten         = Column(String(300), nullable=False)
    duong_dan   = Column(Text)
    loai        = Column(String(20), default="tts")   # tts | record | file
    noi_dung    = Column(Text, default="")
    ban_dich    = Column(Text, default="")             # bản dịch tiếng Việt (lưu cố định)
    giong_doc   = Column(String(100), default="")
    ngon_ngu    = Column(String(20), default="en")
    bai_id      = Column(Integer, ForeignKey("bai.id"))
    tao_luc     = Column(DateTime, default=datetime.now)
    bai         = relationship("Bai", back_populates="audios")


class Video(Base):
    __tablename__ = "video"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    ten         = Column(String(300), nullable=False)
    duong_dan   = Column(Text)
    loai        = Column(String(20), default="file")   # file | youtube
    bai_id      = Column(Integer, ForeignKey("bai.id"))
    tao_luc     = Column(DateTime, default=datetime.now)
    bai         = relationship("Bai", back_populates="videos")


class Flashcard(Base):
    __tablename__ = "flashcard"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    mat_truoc   = Column(Text, nullable=False)
    mat_sau     = Column(Text, default="")
    ghi_chu     = Column(Text, default="")
    hinh_anh    = Column(Text, default="")
    bai_id      = Column(Integer, ForeignKey("bai.id"))
    tao_luc     = Column(DateTime, default=datetime.now)
    lan_xem     = Column(Integer, default=0)
    bai         = relationship("Bai", back_populates="flashcards")


class CauHoi(Base):
    __tablename__ = "cau_hoi"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    noi_dung    = Column(Text, nullable=False)
    hinh_anh    = Column(Text, default="")
    lua_chon_a  = Column(Text, default="")
    lua_chon_b  = Column(Text, default="")
    lua_chon_c  = Column(Text, default="")
    lua_chon_d  = Column(Text, default="")
    lua_chon_e  = Column(Text, default="")
    dap_an      = Column(String(1), default="A")
    giai_thich  = Column(Text, default="")
    ghi_chu     = Column(Text, default="")
    danh_dau    = Column(Boolean, default=False)
    bai_id      = Column(Integer, ForeignKey("bai.id"))
    tao_luc     = Column(DateTime, default=datetime.now)
    bai         = relationship("Bai", back_populates="cau_hois")


class NhatKi(Base):
    __tablename__ = "nhat_ki"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    ngay        = Column(DateTime, default=datetime.now)
    noi_dung    = Column(Text, default="")
    audio_path  = Column(Text, default="")
    loai        = Column(String(20), default="text")
    chu_de_id   = Column(Integer, ForeignKey("chu_de.id"), nullable=True)
    chuong_id   = Column(Integer, ForeignKey("chuong.id"), nullable=True)
    bai_id      = Column(Integer, ForeignKey("bai.id"), nullable=True)
    chu_de      = relationship("ChuDe", back_populates="nhat_kis")
    chuong      = relationship("Chuong", back_populates="nhat_kis")
    bai         = relationship("Bai", back_populates="nhat_kis")


class DoanLap(Base):
    __tablename__ = "doan_lap"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    ten         = Column(String(200), default="Đoạn lặp mới")
    loai_media  = Column(String(20), nullable=False)
    media_id    = Column(Integer, nullable=False)
    thoi_gian_a = Column(Integer, default=0)
    thoi_gian_b = Column(Integer, default=0)
    tao_luc     = Column(DateTime, default=datetime.now)


class VanBanLuyenNho(Base):
    __tablename__ = "van_ban_luyen_nho"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    ten         = Column(String(200), nullable=False, default="Đoạn văn mới")
    noi_dung    = Column(Text, nullable=False)
    bai_id      = Column(Integer, ForeignKey("bai.id"), nullable=True)
    tao_luc     = Column(DateTime, default=datetime.now)
    luyen_lan   = Column(Integer, default=0)
    diem_cao    = Column(Integer, default=0)
    bai         = relationship("Bai", back_populates="van_ban_luyen_nhos")
