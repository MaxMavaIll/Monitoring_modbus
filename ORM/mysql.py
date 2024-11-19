from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from datetime import datetime, timedelta

Base = declarative_base()

def preapation_DB(name_table):
    # Динамічно створюємо клас з потрібною назвою таблиці
    class DynamicTable(Base):
        __tablename__ = name_table
        __table_args__ = {'extend_existing': True}
        id = Column(Integer, primary_key=True, autoincrement=True)
        R = Column(Float)
        timestamp = Column(DateTime(timezone=True))

    return DynamicTable

def connect_DB(host: str = None, user: str = None, password: str = None, database: str = None):
    engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{database}')
    Session = sessionmaker(bind=engine)
    session = Session()
    return session, engine

def add_register_record(
        city: str, 
        time: datetime, 
        R: float = None,
        session=None, engine=None
        ):
    
    inspector = inspect(engine)

    if session is None or engine is None:
        return
    
    if city not in inspector.get_table_names():
        print(f"Table '{city}' does not exist in the database.")
        return False  # Завершуємо функцію, якщо таблиця не існує

    # Створюємо динамічну модель для потрібного міста
    DataBase = preapation_DB(city)

    # Створюємо таблицю, якщо вона ще не існує
    new_record = DataBase(
        R=R, 
        timestamp=time
        )
        
    session.add(new_record)
    session.commit()

def disconnect(session):
    session.close()

