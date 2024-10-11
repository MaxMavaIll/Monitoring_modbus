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
        sensor_id = Column(Integer)
        register = Column(String(50))
        value = Column(String(50))
        timestamp = Column(DateTime, default=datetime.utcnow)

    return DynamicTable

def connect_DB(host: str = None, user: str = None, password: str = None):
    engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{user}')
    Session = sessionmaker(bind=engine)
    session = Session()
    return session, engine

def add_register_record(town, sensor_id, register, value, session=None, engine=None):
    if session is None or engine is None:
        return

    # Створюємо динамічну модель для потрібного міста
    DataBase = create_dynamic_model(town)

    # Створюємо таблицю, якщо вона ще не існує
    Base.metadata.create_all(engine)

    # Додаємо новий запис
    new_record = DataBase(
        sensor_id=sensor_id,
        register=register,
        value=value
    )
    session.add(new_record)
    session.commit()

def disconnect(session):
    session.close()