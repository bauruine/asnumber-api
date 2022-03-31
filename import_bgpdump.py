from datetime import datetime
import os
import re
import psycopg2
from psycopg2 import extras
import yaml
import ipaddress
from bgpdumpy import BGPDump, TableDumpV2
import requests
from asn_app.utils import load_config

def download_file(url, tmp_path):
    """ https://stackoverflow.com/a/16696317 """
    local_filename = url.split('/')[-1]
    full_path = os.path.join(tmp_path, local_filename)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(full_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
    return full_path

def insert_into(db_conn, cursor, prefix_list):
    """ Insert prefixlist into database """

    unique_prefixes = set()
    for single in prefix_list:
        unique_prefixes.add((single[0], single[2]))

    psycopg2.extras.execute_values(
        cursor,
        """
        WITH input_data(prefix, time_now) AS (
            VALUES
            (NULL::cidr, NULL::timestamp),
            %s
            OFFSET 1
        )
            INSERT INTO prefixes (prefix, added_timestamp)
            SELECT prefix, time_now FROM input_data
            ON CONFLICT (prefix) DO UPDATE SET added_timestamp = excluded.added_timestamp
        """, unique_prefixes
    )

    psycopg2.extras.execute_values(
        cursor,
        """
        WITH input_data(prefix, asnumber, time_now) AS (
            VALUES
            (NULL::cidr, NULL::bigint, NULL::timestamp),
            %s
            OFFSET 1
        )
        , asn AS (
            INSERT INTO asnumbers (asnumber, last_updated)
            SELECT asnumber, time_now
            FROM input_data
            ON CONFLICT DO NOTHING
            )
        INSERT INTO asnumbers_prefixes (asnumber, prefix, first_seen, last_seen)
        SELECT asnumber, prefix, time_now, time_now
        FROM input_data 
        ON CONFLICT (asnumber, prefix) DO UPDATE SET last_seen = excluded.first_seen
        """, prefix_list
    )



def main():
    # load config file
    cfg = load_config('config.yml')

    db_conn = psycopg2.connect(dbname=cfg['psql']['dbname'], user=cfg['psql']['user'], host=cfg['psql']['host'], password=cfg['psql']['password'])

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    insert_cur = db_conn.cursor()
    i = 0
    prefix_list = set()
    file_name = download_file(cfg['bgp']['url'], cfg['bgp']['tmp_path'])
    bogons = ['0.0.0.0/0', '0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8',
              '169.254.0.0/16', '172.16.0.0/12', '192.0.0.0/24', '192.0.2.0/24',
              '192.168.0.0/16', '198.18.0.0/15', '198.51.100.0/24', '203.0.113.0/24',
              '224.0.0.0/3', '::/0'
             ]
    with BGPDump(file_name) as bgp:
        for entry in bgp:

            # entry.body can be either be TableDumpV1 or TableDumpV2
            if not isinstance(entry.body, TableDumpV2):
                continue  # I expect an MRT v2 table dump file

            # get a string representation of this prefix
            prefix = '%s/%d' % (entry.body.prefix, entry.body.prefixLength)

            # get a list of each unique originating ASN for this prefix
            originatingASs = set([
                route.attr.asPath.split()[-1]
                for route
                in entry.body.routeEntries])

            for originating_as in originatingASs:
                source_asn = re.sub(r'[^\d]', '', originating_as)
                if len(source_asn) > 15:
                    continue
                for bogon in bogons:
                    if prefix == bogon:
                        print(f"Found bogon {bogon} announced by AS{source_asn}. Replacing by AS0")
                        source_asn = 0
                prefix_list.add((prefix, source_asn, timestamp))

            if i > 500:
                i = 0
                insert_into(db_conn, insert_cur, prefix_list)
                prefix_list = set()
            i += 1



    insert_into(db_conn, insert_cur, prefix_list)
    db_conn.commit()
    insert_cur.close()
    db_conn.close()

main()

