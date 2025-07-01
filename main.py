import os
import toml
import time
import pytz

from datetime import datetime
from modbus_dl.scripts import  modbus_helper
from ORM_MySql.mysql import connect_DB, add_register_record, disconnect, get_daily_averages
from API_sheet.sheets_update import update_sheets
from modbus_dl.utils import initialize_environment, setup_logging

config_toml = toml.load('config.toml')



def get_time_kyiv_with_utc(timestamp: str = None, time_format = '%Y-%m-%d %H:%M:%S%z') -> datetime:
    utc_zone = pytz.timezone('UTC')
    kyiv_zone = pytz.timezone('Europe/Kiev')

    if timestamp is None:
        timestamp_kyiv = datetime.now(kyiv_zone)
        return timestamp_kyiv

    timestamp_utc = datetime.strptime(timestamp, time_format)
    timestamp_kyiv = timestamp_utc.astimezone(kyiv_zone)
    # timestamp_kyiv = timestamp_kyiv.strftime(time_format)

    print("Original UTC time:", timestamp_utc)
    print("Converted Kiev time:", timestamp_kyiv)

    return timestamp_kyiv




def main():
    initialize_environment()
    log = setup_logging()
    log.info("\n##############################################" \
             "\n##############################################")

    averages = {}
    current_time = datetime.now()

    log. info(f"Starting Modbus TCP Data Logger at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    config_path = os.path.realpath(__file__).replace('main.py', 'config.toml')
    modbus_logger = modbus_helper.ModbusTCPDataLogger(
		full_path_to_modbus_config_toml=config_path
	)
    log.info(f"Finished loading configuration from {config_path}")
    log.info("Starting send to DB data ...")
    session, engine = connect_DB(
        host=config_toml['DB']['host'],
        user=config_toml['DB']['user'],
        password=config_toml['DB']['password'],
        database=config_toml['DB']['database']
        )

    for town, records in modbus_logger.data_for_db.items():

        if records is None:
            log.warning(f"No data for {town}, skipping...")
            add_register_record(
                town=town, session=session, engine=engine, 
                timestamp=get_time_kyiv_with_utc())
            continue
        
        time_utc = records.get('timestamp_utc')
        kyiv_time = get_time_kyiv_with_utc(time_utc)

        compound = records.get('compound')
        if not compound:
            compound = {}

        log.info(f"Processing data for {town} at {kyiv_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log.debug(f"Compound data: {compound}")
        add_register_record(
            town=town, 
            CO=compound.get('CO'), SO2=compound.get('SO2'), NO2=compound.get('NO2'), 
            NO=compound.get('NO'), H2S=compound.get('H2S'), O3=compound.get('O3'), 
            NH3=compound.get('NH3'), PM2_5=compound.get('PM2_5'), PM10=compound.get('PM10'), 
            timestamp = kyiv_time, session=session, engine=engine
            )
        
        if current_time.hour == 0 and current_time.minute == 0:
            log.info(f"Updating daily averages for {town} at" \
                     f"{kyiv_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if town not in averages:
                averages[town]= get_daily_averages(town=town, session=session, engine=engine)
           
    if averages != {}:
        log.info("Averages for the day are ready, updating sheets...")
        update_sheets(data=modbus_logger.data_for_db, averages=averages)
    elif current_time.minute == 0: 
        log.warning("No data to update in sheets, averages are empty.")
        update_sheets(data=modbus_logger.data_for_db)

    disconnect(session)
    log.info("Finished sending data to DB and updating sheets.")


if __name__ == "__main__":
    log = setup_logging()

    try:
        start_time = time.time() 
        main()  
        end_time = time.time()  

        execution_time = end_time - start_time
        log.info(f"TIME WORK {execution_time:.4f} sec.")
    except Exception as e:
        log.error(f"An error occurred: {e}", exc_info=True)