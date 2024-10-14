import os, toml

from modbus_dl.scripts import  modbus_helper
from ORM_MySql.connect_mysql import connect_DB, add_register_record, disconnect

config_toml = toml.load('config.toml')


def main():
    config_path = os.path.realpath(__file__).replace('main.py', 'config.toml')
    modbus_logger = modbus_helper.ModbusTCPDataLogger(
		full_path_to_modbus_config_toml=config_path
	)		

    session, engine = connect_DB(
        host=config_toml['DB']['host'],
        user=config_toml['DB']['user'],
        password=config_toml['DB']['password']
        )
    print(modbus_logger.data_for_db)

    for town, records in modbus_logger.data_for_db.items():
        if records is None:
            add_register_record(
                town=town, session=session, engine=engine)
            continue

        add_register_record(
            town=town, 
            CO=records.get('CO'), SO2=records.get('SO2'), NO2=records.get('NO2'), 
            NO=records.get('NO'), H2S=records.get('H2S'), O3=records.get('O3'), 
            NH3=records.get('NH3'), PM2_5=records.get('PM2.5'), PM10=records.get('PM10'), 
            timestamp = records.get('timestamp_utc'), session=session, engine=engine
            )

    disconnect(session)


if __name__ == "__main__":
    main()