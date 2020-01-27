""" Script to download asnumber information """
import yaml
import requests
import dns.resolver
import psycopg2
from asn_app.asn import add_asn

def main():
    resolver = dns.resolver.Resolver()

    # load config file
    with open("config.yml", 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    db_conn = psycopg2.connect(dbname=cfg['psql']['dbname'], user=cfg['psql']['user'], host=cfg['psql']['host'], password=cfg['psql']['password'])

    select_cur = db_conn.cursor()
    insert_cur = db_conn.cursor()

    req_session = requests.Session()

    select_cur.execute('SELECT distinct(asnumber) FROM asnumbers_prefixes;')
    for asn_tup in select_cur:
        add_asn(db_conn, resolver, req_session, asn_tup[0])


    insert_cur.close()
    select_cur.close()
    db_conn.close()

main()
