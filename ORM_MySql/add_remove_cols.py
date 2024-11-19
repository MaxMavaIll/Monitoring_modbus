from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, inspect, text
import toml

config_toml = toml.load('config.toml')

def remove_columns_if_exist(engine, table_name, columns):
    inspector = inspect(engine)
    
    existing_columns = [column['name'] for column in inspector.get_columns(table_name)]
    
    for column_name in columns:
        if column_name in existing_columns:
            alter_query = text(f'ALTER TABLE {table_name} DROP COLUMN {column_name}')
            with engine.connect() as connection:
                connection.execute(alter_query)
                print(f"Column '{column_name}' has been dropped from table '{table_name}'.")

def add_columns_if_not_exist(engine, table_name, columns):
    inspector = inspect(engine)
    
    
    if table_name not in inspector.get_table_names():
        print(f"Table '{table_name}' does not exist in the database.")
        return False 
     
    existing_columns = [column['name'] for column in inspector.get_columns(table_name)]
    
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            if column_type is Float:
                type_name = 'FLOAT'
            elif column_type is Integer:
                type_name = 'INTEGER'
            elif column_type is String:
                type_name = 'VARCHAR(255)'  
            elif column_type is DateTime:
                type_name = 'DATETIME'
            else:
                type_name = 'TEXT'  
            
            alter_query = text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {type_name}')
            with engine.connect() as connection:
                connection.execute(alter_query)

    print(f"Columns checked and updated for table '{table_name}'.")


    
user = config_toml['DB']['user']
password = config_toml['DB']['password']
host = config_toml['DB']['host']
database = config_toml['DB']['database']
engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{database}')

for city in config_toml['cities'].values():
    if city in ['Bila_Tserkva', 'Pidhirtsi', 'Brovary']:
        continue

    # add_columns_if_not_exist(engine, city, {'R': Float})
    # remove_columns_if_exist(engine, 'Bohuslav', ['R'])