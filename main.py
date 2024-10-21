import os, toml, datetime, time

from modbus_dl.scripts import  modbus_helper
from ORM_MySql.connect_mysql import connect_DB, add_register_record, disconnect, get_daily_averages
from API_sheet.sheets_update import update_sheets

config_toml = toml.load('config.toml')


def main(time_format = '%Y-%m-%d %H:%M:%S%z'):
    averages = {}
    current_time = datetime.datetime.now()

    config_path = os.path.realpath(__file__).replace('main.py', 'config.toml')
    modbus_logger = modbus_helper.ModbusTCPDataLogger(
		full_path_to_modbus_config_toml=config_path
	)		

    session, engine = connect_DB(
        host=config_toml['DB']['host'],
        user=config_toml['DB']['user'],
        password=config_toml['DB']['password']
        )

    for town, records in modbus_logger.data_for_db.items():
        if records is None:
            add_register_record(
                town=town, session=session, engine=engine)
            continue

        compound = records['compound']
        timestamp = datetime.datetime.strptime(records.get('timestamp_utc'), time_format)

        add_register_record(
            town=town, 
            CO=compound.get('CO'), SO2=compound.get('SO2'), NO2=compound.get('NO2'), 
            NO=compound.get('NO'), H2S=compound.get('H2S'), O3=compound.get('O3'), 
            NH3=compound.get('NH3'), PM2_5=compound.get('PM2_5'), PM10=compound.get('PM10'), 
            timestamp = timestamp, session=session, engine=engine
            )
        
        if current_time.hour == 0 and current_time.minute == 0:
            if town not in averages:
                averages[town]= get_daily_averages(town=town, session=session, engine=engine)
           
    if averages != {}:
        update_sheets(data=modbus_logger.data_for_db, averages=averages)
    elif current_time.minute == 0: 
        update_sheets(data=modbus_logger.data_for_db)

    update_sheets(data=modbus_logger.data_for_db)

    disconnect(session)

if __name__ == "__main__":
    start_time = time.time()  # Початок вимірювання часу
    main()  # Виклик функції main
    end_time = time.time()  # Кінець вимірювання часу

    execution_time = end_time - start_time  # Обчислення тривалості виконання
    print(f"Функція main виконувалася {execution_time:.4f} секунд.")