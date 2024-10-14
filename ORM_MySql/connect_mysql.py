from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

def create_dynamic_model(name_table):
    # Динамічно створюємо клас з потрібною назвою таблиці
    class DynamicTable(Base):
        __tablename__ = name_table
        __table_args__ = {'extend_existing': True}
        id = Column(Integer, primary_key=True, autoincrement=True)
        CO = Column(String(15))
        SO2 = Column(String(15))
        NO2 = Column(String(15))
        NO = Column(String(15))
        H2S = Column(String(15))
        O3 = Column(String(15))
        NH3 = Column(String(15))
        PM2_5=Column(String(15))
        PM10=Column(String(15))
        timestamp = Column(DateTime, default=datetime.utcnow)

    return DynamicTable

def connect_DB(host: str = None, user: str = None, password: str = None):
    engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{user}')
    Session = sessionmaker(bind=engine)
    session = Session()
    return session, engine

def add_register_record(
        town, 
        CO=None, SO2=None, NO2=None, 
        NO=None, H2S=None, O3=None, 
        NH3=None, PM2_5=None, PM10=None, 
        timestamp: DateTime = None,  session=None, engine=None
        ):
    if session is None or engine is None:
        return

    # Створюємо динамічну модель для потрібного міста
    DataBase = create_dynamic_model(town)

    # Створюємо таблицю, якщо вона ще не існує
    Base.metadata.create_all(engine)

    # Додаємо новий запис
    new_record = DataBase(
        CO=CO,
        SO2=SO2,
        NO2=NO2,
        NO=NO,
        H2S=H2S,
        O3=O3,
        NH3=NH3,
        PM2_5=PM2_5,
        PM10=PM10,
        timestamp=datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S%z'),
    )
    session.add(new_record)
    session.commit()

def disconnect(session):
    session.close()