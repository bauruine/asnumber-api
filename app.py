import logging
import psycopg2
import ipaddress
from flask import Flask
from flask import request
from flask import jsonify


app = Flask(__name__)

# configure logfile
logging.basicConfig(filename='api.log', level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

# create database connection
db_conn = conn = psycopg2.connect("dbname=asnumber user=asnumber host=10.0.3.11 password=Eecee4phiCeezeejohQuohmaht7aixoofi4aisairohng4aish")
cursor = db_conn.cursor()


@app.route('/asnum/<ip>', methods=['GET'])
def response_asn(ip):
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
            return jsonify(success='false', status='400', message='not a valid ip address'), 400

        prefix_result = cursor.fetchone()
        logging.debug(prefix_result)
        if prefix_result:
            cursor.execute("SELECT * FROM asnumbers WHERE asnumber = %s LIMIT 1;", (prefix_result[1],))
            asn = cursor.fetchone()
            if asn:
                cursor.execute("SELECT COUNT(*) FROM v4prefixes WHERE asnumber = %s;", (asn[0],))
                v4prefixes = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM v6prefixes WHERE asnumber = %s;", (asn[0],))
                v6prefixes = cursor.fetchone()[0]
                numprefixes = v4prefixes + v6prefixes

                return jsonify(asn=asn[0], prefixes=numprefixes, asname=asn[1], asdesc=asn[2], country=asn[3], rir=asn[4], prefix=prefix_result[0])
            else:
                return jsonify(message="no asn found")
        else:
            return jsonify(message="no prefix found")

@app.route('/subnet/<asn>/<version>', methods=['GET'])
@app.route('/subnet/<asn>', defaults={'version': 'both'}, methods=['GET'])
def response_subnet(asn, version):
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

