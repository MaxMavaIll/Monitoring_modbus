from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from datetime import datetime, timedelta

Base = declarative_base()

def create_dynamic_model(name_table):
    # Динамічно створюємо клас з потрібною назвою таблиці
    class DynamicTable(Base):
        __tablename__ = name_table
        __table_args__ = {'extend_existing': True}
        id = Column(Integer, primary_key=True, autoincrement=True)
        CO = Column(Float)
        SO2 = Column(Float)
        NO2 = Column(Float)
        NO = Column(Float)
        H2S = Column(Float)
        O3 = Column(Float)
        NH3 = Column(Float)
        PM2_5=Column(Float)
        PM10=Column(Float)
        timestamp = Column(DateTime(timezone=True))

    return DynamicTable

def connect_DB(host: str = None, user: str = None, password: str = None, database: str = None):
    engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{database}')
    Session = sessionmaker(bind=engine)
    session = Session()
    return session, engine

def add_register_record(
        town, timestamp: datetime, 
        CO=None, SO2=None, NO2=None, 
        NO=None, H2S=None, O3=None, 
        NH3=None, PM2_5=None, PM10=None,  
        session=None, engine=None
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
        timestamp=timestamp,
    )
    session.add(new_record)
    session.commit()

def disconnect(session):
    session.close()

def get_daily_averages(town, session, engine):
    # Визначаємо час доби тому
    one_day_ago = datetime.utcnow() - timedelta(days=1)

    # Створюємо динамічну модель для конкретного міста
    DataBase = create_dynamic_model(town)

    # Виконуємо запит до бази для обчислення середніх значень
    averages = session.query(
        func.avg(DataBase.CO).label('CO'),
        func.avg(DataBase.SO2).label('SO2'),
        func.avg(DataBase.NO2).label('NO2'),
        func.avg(DataBase.NO).label('NO'),
        func.avg(DataBase.H2S).label('H2S'),
        func.avg(DataBase.O3).label('O3'),
        func.avg(DataBase.NH3).label('NH3'),
        func.avg(DataBase.PM2_5).label('PM2_5'),
        func.avg(DataBase.PM10).label('PM10')
    ).filter(DataBase.timestamp >= one_day_ago).first()

    # Повертаємо середні значення
    return {
    'CO': round(averages.CO, 3) if averages.CO is not None else None,
    'SO2': round(averages.SO2, 3) if averages.SO2 is not None else None,
    'NO2': round(averages.NO2, 3) if averages.NO2 is not None else None,
    'NO': round(averages.NO, 3) if averages.NO is not None else None,
    'H2S': round(averages.H2S, 3) if averages.H2S is not None else None,
    'O3': round(averages.O3, 3) if averages.O3 is not None else None,
    'NH3': round(averages.NH3, 3) if averages.NH3 is not None else None,
    'PM2_5': round(averages.PM2_5, 3) if averages.PM2_5 is not None else None,
    'PM10': round(averages.PM10, 3) if averages.PM10 is not None else None
}