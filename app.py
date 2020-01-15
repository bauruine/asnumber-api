import logging
import re
import yaml
import ipaddress
import psycopg2
import psycopg2.extras
import dns.resolver
from flask import Flask
from flask import request
from flask import jsonify
from flask import g


app = Flask(__name__)

# configure logfile
logging.basicConfig(filename='api.log', level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

# load config file
with open("config.yml", 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)



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
    insert_cur = db_conn.cursor()
    try:
        answers = resolver.query("AS" + str(asn) + ".asn.cymru.com", "TXT")
        for details in answers:
            parsed = re.search(r'\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*) ?-?\s?(.*),', str(details))
            if parsed:
                insert_cur.execute("INSERT INTO asnumbers (asnumber, asname, asdescription, country, RIR) VALUES (%s, %s, %s, %s, %s)", (asn, parsed.group(4), parsed.group(5), parsed.group(1), parsed.group(2)))
                db_conn.commit()
            return True
        return False
    except dns.exception.DNSException as e:
        logging.error(e)
        return False

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
        cursor.execute("SELECT prefix,asnumber FROM get_prefix(%s);", (ip,))

        prefix_result = cursor.fetchone()
        if prefix_result:
            asn = get_asn_info(prefix_result[1])
            if not asn:
                update_asn_info(prefix_result[1])
                asn = get_asn_info(prefix_result[1])

            if asn:
                cursor.execute("SELECT COUNT(*) FROM prefixes WHERE asnumber = %s;", (asn[0],))
                prefixes = cursor.fetchone()[0]
                return jsonify(asn=asn[0], prefixes=prefixes, asname=asn[1], asdesc=asn[2], country=asn[3], rir=asn[4], prefix=prefix_result[0])
            return jsonify(message="no asn found")
        return jsonify(message="no prefix found")

@app.route('/subnet/<asn>/<version>', methods=['GET'])
@app.route('/subnet/<asn>', defaults={'version': 'both'}, methods=['GET'])
def response_subnet(asn, version):
    ''' Return all announced subnets for a specific ASN '''

    db_conn = get_db()
    cursor = db_conn.cursor()

    cursor.execute('SELECT prefix FROM prefixes WHERE asnumber = %s;', (asn,))
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
            cursor.execute('select * from asnumbers where asnumber = %s', (asn,))

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

