import requests
import datetime
import json
import toml

config_toml = toml.load('config.toml')


url = {
    "update": config_toml['sheets']['url_apps_script'],
}

def update_sheets(data: dict = {}):
    tmp = {}
    if 'cities' not in tmp:
        tmp['cities'] = config_toml['cities']

    if 'data' not in tmp:
        tmp['data'] = data

    json_data = json.dumps(tmp)

    tmp = requests.post(
        url["update"], data={'data': json_data},
        headers={'Content-Type': 'application/x-www-form-urlencoded'
        })
    print(tmp.text)