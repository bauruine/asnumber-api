import logging
import re
import yaml
import ipaddress
import psycopg2
import dns.resolver
from flask import Flask
from flask import request
from flask import jsonify


app = Flask(__name__)

# configure logfile
logging.basicConfig(filename='api.log', level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

# load config file
with open("config.yml", 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)


# create database connection
db_conn = psycopg2.connect(dbname=cfg['psql']['dbname'], user=cfg['psql']['user'], host=cfg['psql']['host'], password=cfg['psql']['password'])
cursor = db_conn.cursor()


def update_asn_info(asn: int) -> bool:
    ''' Update ASN details if not already in the database '''
    resolver = dns.resolver.Resolver()
    insert_cur = db_conn.cursor()
    try:
        answers = resolver.query("AS" + str(asn) + ".asn.cymru.com", "TXT")
        for details in answers:
            parsed = re.search(r'\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*) ?-?\s?(.*),', str(details))
            if parsed:
                insert_cur.execute("INSERT INTO asnumbers (asnumber, asname, asdescription, country, RIR) VALUES (%s, %s, %s, %s, %s)", (asn, parsed.group(4), parsed.group(5), parsed.group(1), parsed.group(2)))
                db_conn.commit()
            return True
    except dns.exception.DNSException as e:
        logging.error(e)
        return False

def get_asn_info(asn: int) -> tuple:
    ''' Get the ASN info '''
    cursor.execute("SELECT * FROM asnumbers WHERE asnumber = %s LIMIT 1;", (asn,))
    return cursor.fetchone()

@app.route('/asnum/<ip>', methods=['GET'])
def response_asn(ip):
    ''' Send ASN details for request '''
    if ip:
        try:
            ipaddr = ipaddress.ip_address(ip)
        except ValueError as e:
            logging.debug(e)
            return jsonify(success='false', status='400', message='not a valid ip address'), 400
        if ipaddr.version == 4:
            cursor.execute("SELECT prefix,asnumber FROM get_v4prefix(%s);", (ip,))
        elif ipaddr.version == 6:
            cursor.execute("SELECT prefix,asnumber FROM get_v6prefix(%s);", (ip,))
        else:
            return jsonify(success='false', status='400', message='not known ip address type'), 400

        prefix_result = cursor.fetchone()
        logging.debug(prefix_result)
        if prefix_result:
            asn = get_asn_info(prefix_result[1])
            if not asn:
                update_asn_info(prefix_result[1])
                asn = get_asn_info(prefix_result[1])

            if asn:
                cursor.execute("SELECT COUNT(*) FROM v4prefixes WHERE asnumber = %s;", (asn[0],))
                v4prefixes = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM v6prefixes WHERE asnumber = %s;", (asn[0],))
                v6prefixes = cursor.fetchone()[0]
                numprefixes = v4prefixes + v6prefixes
                return jsonify(asn=asn[0], prefixes=numprefixes, asname=asn[1], asdesc=asn[2], country=asn[3], rir=asn[4], prefix=prefix_result[0])
            return jsonify(message="no asn found")
        return jsonify(message="no prefix found")

@app.route('/subnet/<asn>/<version>', methods=['GET'])
@app.route('/subnet/<asn>', defaults={'version': 'both'}, methods=['GET'])
def response_subnet(asn, version):
    ''' Return all announced subnets for a specific ASN '''
    if version == 'both' or version == 'v4':
        cursor.execute('SELECT prefix FROM v4prefixes WHERE asnumber = %s;', (asn,))
        v4prefixes = cursor.fetchall()
    if version == 'both' or version == 'v6':
        cursor.execute('SELECT prefix FROM v6prefixes WHERE asnumber = %s;', (asn,))
        v6prefixes = cursor.fetchall()
    full = ""

    if version == 'both' or version == 'v4':
        for prefix in v4prefixes:
            full += prefix[0] + "\n"
    if version == 'both' or version == 'v6':
        for prefix in v6prefixes:
            full += prefix[0] + "\n"
    return full


@app.route('/healthcheck', methods=['GET'])
def respond_healthcheck():
    return "200 OK"


if __name__ == '__main__':
    app.run()

