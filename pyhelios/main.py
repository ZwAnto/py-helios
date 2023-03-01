import json
import os

import influxdb_client
import requests
from dotenv import dotenv_values
from influxdb_client.client.write_api import SYNCHRONOUS

config = {
    **dotenv_values(".env"),
    **os.environ
}

if __name__ == '__main__':

    client = influxdb_client.InfluxDBClient(
    url=config.get('SOCKY_INFLUX_URL'),
    token=config.get('SOCKY_INFLUX_TOKEN'),
    org=config.get('SOCKY_INFLUX_ORG')
    )

    query_api = client.query_api()

    lastRadiation = query_api.query('''
    from(bucket: "infoclimat")
    |> range(start: -2h, stop: now())
    |> filter(fn: (r) => r["_measurement"] == "prometheus")
    |> filter(fn: (r) => r["_field"] == "radiation_solaire")
    |> aggregateWindow(every: 1h, fn: last, createEmpty: false)
    |> yield(name: "last")
    ''')

    if len(lastRadiation):

        records = lastRadiation[0].records

        if len(records) < 2:
            print("Not enougth records")
            exit()

        radiationOk = all([i['_value'] > 250 for i in records])

        if not radiationOk:
            print("Not enougth radiation")
            exit()

        r = requests.post(config.get('TYDOMAPI_URL') + '/refresh/all')
        assert r.status_code == 200

        r = requests.get(config.get('TYDOMAPI_URL') + '/devices/' + config.get('DEVICE_ID') + '/data')
        assert r.status_code == 200

        data = r.json()['content']['data']
        position = [i['value'] for i in data if i['name'] == 'position'][0]

        if position > 0:
            print("Already open")
            exit()
                
        r = requests.put(config.get('TYDOMAPI_URL') + '/devices/' + config.get('DEVICE_ID') + '/data', json.dumps({'name': 'position', 'value': 100}))
        assert r.status_code == 200
        print("Here shine the sun")

    exit()