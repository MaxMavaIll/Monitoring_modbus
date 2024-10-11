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

    for town, records in modbus_logger.data_for_db.items():
        if records is None:
            add_register_record(town=town, sensor_id=None, register=None, value=None, session=session, engine=engine)
            continue

        for id, registers in records.items():
            for register, value in registers.items():
                compound = config_toml.get('compound', {}).get(town, {}).get(id, {}).get(register)

                formatted_value = f'{value / 1000}' if compound is None else f'{value / 1000} {compound}'

                add_register_record(town=town, sensor_id=id, register=register, value=formatted_value, session=session, engine=engine)

    disconnect(session)


if __name__ == "__main__":
    main()