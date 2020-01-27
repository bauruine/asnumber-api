import logging
import re
import ipaddress
import yaml
import requests
import psycopg2
import psycopg2.extras
import dns.resolver
from flask import Flask
from flask import request
from flask import jsonify
from flask import g
from asn_app.asn import add_asn
from asn_app.utils import load_config


app = Flask(__name__)

# configure logfile
logging.basicConfig(filename='api.log', level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

# load config file
cfg = load_config('config.yml')


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = psycopg2.connect(dbname=cfg['psql']['dbname'], user=cfg['psql']['user'], host=cfg['psql']['host'], password=cfg['psql']['password'])
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def update_asn_info(asn: int) -> bool:
    ''' Update ASN details if not already in the database '''
    resolver = dns.resolver.Resolver()
    db_conn = get_db()
    req_session = requests.Session()
    add_asn(db_conn, resolver, req_session, asn)

def get_asn_info(asn: int) -> tuple:
    ''' Get the ASN info '''
    db_conn = get_db()
    cursor = db_conn.cursor()

    cursor.execute("SELECT * FROM asnumbers WHERE asnumber = %s LIMIT 1;", (asn,))
    return cursor.fetchone()

@app.route('/asnum/<ip>', methods=['GET'])
def response_asn(ip):
    ''' Send ASN details for request '''
    db_conn = get_db()
    cursor = db_conn.cursor()

    if ip:
        try:
            ipaddr = ipaddress.ip_address(ip)
        except ValueError as e:
            logging.error(e)
            return jsonify(success='false', status='400', message='not a valid ip address'), 400
        cursor.execute("SELECT prefix FROM prefixes WHERE %s << prefix ORDER BY added_timestamp DESC, prefix DESC LIMIT 1;", (ip,))

        prefix_result = cursor.fetchone()
        if prefix_result:
            cursor.execute("SELECT asnumber FROM asnumbers_prefixes WHERE prefix = %s;", (prefix_result[0],))
            source_asns = cursor.fetchall()

            asn_list = []
            for asnumber in source_asns:
                asns = get_asn_info(asnumber[0])
                if not asns[1]:
                    update_asn_info(asnumber[0])
                    asns = get_asn_info(asnumber[0])
                asn_list.append(asns)

            response_list = []
            for asn in asn_list:
                if asn:
                    cursor.execute("SELECT count(prefixes.prefix) FROM prefixes, asnumbers_prefixes WHERE prefixes.prefix = asnumbers_prefixes.prefix AND asnumber = %s;", (asn[0],))
                    prefixes = cursor.fetchone()[0]
                    response_list.append({'asn': asn[0], 'prefixes': prefixes, 'asname': asn[1],
                                          'asdesc': asn[2], 'country': asn[3], 'rir': asn[4], 'prefix': prefix_result[0]})
            if response_list:
                return jsonify(response_list)
            return jsonify(message="no asn found")
        return jsonify(message="no prefix found")

@app.route('/subnet/<asn>/<version>', methods=['GET'])
@app.route('/subnet/<asn>', defaults={'version': 'both'}, methods=['GET'])
def response_subnet(asn, version):
    ''' Return all announced subnets for a specific ASN '''

    db_conn = get_db()
    cursor = db_conn.cursor()

    cursor.execute('SELECT prefixes.prefix FROM prefixes, asnumbers_prefixes WHERE prefixes.prefix = asnumbers_prefixes.prefix AND asnumber = %s;', (asn,))
    prefixes = cursor.fetchall()
    full = ""

    for prefix in prefixes:
        ip_version = ipaddress.ip_network(prefix, False).version
        if version in ('both', 'v4'):
            versions = [4]
        if version in ('both', 'v6'):
            versions.append(6)
        if ip_version in versions:
            full += prefix[0] + "\n"
    return full


@app.route('/asn/<asn>', methods=['GET'])
def response_asn_details(asn):
    ''' Return asn details for a specific ASN '''

    db_conn = get_db()
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


    response_dict = {}
    if asn.isnumeric() or 'all':
        if asn == "all":
            cursor.execute('SELECT * FROM asnumbers')
        else:
            cursor.execute('SELECT * FROM asnumbers WHERE asnumber = %s', (asn,))

        asns = cursor.fetchall()

        response_dict['status_code'] = 200
        response_dict['status'] = 'ok'
        response_dict['data'] = asns
    else:
        response_dict['status_code'] = 400
        response_dict['status'] = 'asn needs to be a integer'



    return jsonify(response_dict)

@app.route('/healthcheck', methods=['GET'])
def respond_healthcheck():
    return "200 OK"


if __name__ == '__main__':
    app.run()

