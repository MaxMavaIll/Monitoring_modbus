import logging
import toml
import pytz


from sock.sock_connect import Socket
from ORM.mysql import connect_DB, disconnect, add_register_record
from datetime import datetime

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
    session, engine = connect_DB(
        host=config_toml['DB']['host'],
        user=config_toml['DB']['user'],
        password=config_toml['DB']['password'],
        database=config_toml['DB']['database']
    )

    for city in config_toml['city']:
        
        server_connect = Socket(config_toml['city'][city]['ip'], config_toml['port'])

        if not server_connect.status_connect:
            continue

        if not server_connect.send_request_hex():
            continue    
        
        radiation_value = server_connect.decipher_answer_for_radiation()
        print(radiation_value)

        time_kyiv = get_time_kyiv_with_utc()
        add_register_record(
            city=city,
            time=time_kyiv,
            R=radiation_value, 
            session=session,
            engine=engine
        )

        server_connect.disconnect()
    
    disconnect(session=session)


if __name__ == '__main__':
    main()