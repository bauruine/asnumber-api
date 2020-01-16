from datetime import datetime
import re
import psycopg2
from psycopg2 import extras
import yaml
import ipaddress
from bgpdumpy import BGPDump, TableDumpV2

def main():
    # load config file
    with open("../config.yml", 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    db_conn = psycopg2.connect(dbname=cfg['psql']['dbname'], user=cfg['psql']['user'], host=cfg['psql']['host'], password=cfg['psql']['password'])

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    insert_cur = db_conn.cursor()
    i = 0
    prefix_list = []
    with BGPDump('/tmp/latest-bview.gz') as bgp:
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

            # TODO: Multiple source ASNs are not handled at the moment
            if len(originatingASs) > 1:
                asn_list = ', '.join(originatingASs)
                #print(f"{prefix} has multiple source ASN {asn_list}")
            source_asn = re.sub(r'[^\d]', '', originatingASs.pop())

            if len(source_asn) > 15:
                continue
            prefix_list.append((prefix, source_asn, timestamp))

            if i > 10000:
                i = 0
                psycopg2.extras.execute_values(insert_cur, "INSERT INTO prefixes (prefix, asnumber, timestamp) VALUES %s", prefix_list)
                db_conn.commit()
                prefix_list = []
            i += 1



    psycopg2.extras.execute_values(insert_cur, "INSERT INTO prefixes (prefix, asnumber, timestamp) VALUES %s", prefix_list)
    db_conn.commit()
    insert_cur.close()
    db_conn.close()

main()

