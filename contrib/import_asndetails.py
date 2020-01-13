""" Script to download asnumber information """
import re
import yaml
import requests
import dns.resolver
import psycopg2

def get_asdesc_ripe(asn, req_session, reg):
    """ returns the ASN description from RIPE NCC """
    r = req_session.get('https://stat.ripe.net/data/as-overview/data.json?resource=AS' + str(asn))
    if r:
        description = r.json()['data']['holder']
        if description:
            parsed = reg.search(description)
            if parsed:
                description = parsed.group(2)
                return description
    return ''

def get_asdesc_peeringdb(asn, req_session):
    """ return the ASN description from peeringdb """
    r = req_session.get('https://peeringdb.com/api/net?asn=' + str(asn))
    if r:
        asn_id = r.json()['data'][0]['id']
        s = req_session.get('https://www.peeringdb.com/api/net/' + str(asn_id))
        if s:
            description = s.json()['data'][0]['org']['name']
            return description
    return ''


def main():
    resolver = dns.resolver.Resolver()

    # load config file
    with open("../config.yml", 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)

    db_conn = psycopg2.connect(dbname=cfg['psql']['dbname'], user=cfg['psql']['user'], host=cfg['psql']['host'], password=cfg['psql']['password'])

    select_cur = db_conn.cursor()
    insert_cur = db_conn.cursor()

    req_session = requests.Session()
    regex = re.compile(r'(.+) - (.+)')


    tables = ['v4prefixes', 'v6prefixes']
    for table in tables:
        if table == 'v4prefixes':
            select_cur.execute('select distinct(asnumber) from v4prefixes;')
        else:
            select_cur.execute('select distinct(asnumber) from v6prefixes;')

        for asn_tup in select_cur:
            try:
                asn = asn_tup[0]
                answers = resolver.query("AS" + str(asn) + ".asn.cymru.com", "TXT")
                for details in answers:
                    parsed = re.search(r'\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*) ?-?\s?(.*),', str(details))
                    if parsed:
                        as_desc = get_asdesc_peeringdb(asn, req_session)
                        if as_desc:
                            description = as_desc
                            print(f'{asn} peeringdb with desctiption: {description}')
                        else:
                            description = get_asdesc_ripe(asn, req_session, regex)
                            if description:
                                print(f'{asn} ripencc with description: {description}')
                            else:
                                print(f'{asn} could not find as description')
                        insert_cur.execute('SELECT asnumber FROM asnumbers WHERE asnumber = %s;', ([asn]))
                        if insert_cur.fetchone() is None:
                            insert_cur.execute("INSERT INTO asnumbers (asnumber, asname, asdescription, country, RIR) VALUES (%s, %s, %s, %s, %s)", (asn, parsed.group(4), description, parsed.group(1), parsed.group(2)))
                        else:
                            insert_cur.execute("UPDATE asnumbers set asnumber = %s, asname = %s, asdescription = %s, country = %s, rir = %s WHERE asnumber = %s", (asn, parsed.group(4), description, parsed.group(1), parsed.group(2), asn))

                        db_conn.commit()

            except dns.exception.DNSException as e:
                print(e)
                continue


        insert_cur.close()
        select_cur.close()
        db_conn.close()

main()
