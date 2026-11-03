from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./rpg.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    next_level_xp = Column(Integer, default=100)
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    
    strength = Column(Integer, default=5)
    agility = Column(Integer, default=5)
    vitality = Column(Integer, default=5)
    intelligence = Column(Integer, default=5)
    perception = Column(Integer, default=5)
    luck = Column(Integer, default=5)
    
    stat_points = Column(Integer, default=0)
    ability_points = Column(Integer, default=0)
    
    inventory = Column(JSON, default=list)
    abilities = Column(JSON, default=list)
    equipment = Column(JSON, default=dict)
    quests = Column(JSON, default=list)
    history = Column(JSON, default=list)
    location = Column(String, default="Неизвестно")
    
    enemy = Column(JSON, default=dict) # <-- ДЛЯ БУДУЩЕЙ БОЕВКИ
    book_file = Column(String, default="")

Base.metadata.create_all(bind=engine)