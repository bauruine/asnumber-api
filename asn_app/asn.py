""" Script to download asnumber information """
import re
import subprocess
import requests
import dns.resolver

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

def get_asdesc_whois(asn):
    """ return the ASN description from peeringdb """
    result = subprocess.run(['/usr/bin/whois', f'AS{asn}'], capture_output=True)
    try:
        parsed = re.search(r'(OrgName|owner|org-name):\W+(.+?)\n', result.stdout.decode())
    except UnicodeDecodeError as e:
        return ''
    if parsed:
        return parsed.group(2)
    return ""

def add_asn(db_conn, resolver, req_session, asn):

    select_cur = db_conn.cursor()
    insert_cur = db_conn.cursor()

    regex = re.compile(r'(.+) - (.+)')


    try:
        answers = resolver.query("AS" + str(asn) + ".asn.cymru.com", "TXT")
        for details in answers:
            parsed = re.search(r'\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*) ?-?\s?(.*),', str(details))
            if parsed:
                as_desc = get_asdesc_peeringdb(asn, req_session)
                if as_desc:
                    description = as_desc
                    print(f'{asn} peeringdb with desctiption: {description}')
                else:
                    description = get_asdesc_whois(asn)
                    if description:
                        print(f'{asn} whois with description: {description}')
                    else:
                        description = get_asdesc_ripe(asn, req_session, regex)
                        if description:
                            print(f'{asn} ripencc with description: {description}')
                        else:
                            print(f'{asn} could not find as description')
                insert_cur.execute("UPDATE asnumbers set asnumber = %s, asname = %s, asdescription = %s, country = %s, rir = %s WHERE asnumber = %s", (asn, parsed.group(4), description, parsed.group(1), parsed.group(2), asn))

                db_conn.commit()

    except dns.exception.DNSException as e:
        print(e)


    insert_cur.close()
    select_cur.close()
