import re
import dns.resolver
import requests
import psycopg2

resolver = dns.resolver.Resolver()

db_conn = conn = psycopg2.connect("dbname=asnumber user=asnumber host=10.0.3.11 password=Eecee4phiCeezeejohQuohmaht7aixoofi4aisairohng4aish")
select_cur = db_conn.cursor()
insert_cur = db_conn.cursor()

update_entries = False

csv = ''
i = 0

tables = ['v4prefixes', 'v6prefixes']
for table in tables:
    select_cur.execute('select distinct(asnumber) from %s;', (table))
    for asn_tup in select_cur:
        try:
            asn = asn_tup[0]
            answers = resolver.query("AS" + str(asn) + ".asn.cymru.com", "TXT")
            for details in answers:
                parsed = re.search(r'\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*)\s*\|\s*(\S*) ?-?\s?(.*),', str(details))
                if parsed:
                    insert_cur.execute('SELECT asnumber FROM asnumbers WHERE asnumber = %s;', ([asn]))
                    if insert_cur.fetchone() is None:
                        insert_cur.execute("INSERT INTO asnumbers (asnumber, asname, asdescription, country, RIR) VALUES (%s, %s, %s, %s, %s)", (asn, parsed.group(4), parsed.group(5), parsed.group(1), parsed.group(2)))
                    elif update_entries:
                        insert_cur.execute("UPDATE asnumbers set asnumber = %s, asname = %s, asdescription = %s, country = %s, rir = %s WHERE asnumber = %s", (asn, parsed.group(4), parsed.group(5), parsed.group(1), parsed.group(2), asn))
                    else:
                        continue

                    db_conn.commit()

        except dns.exception.DNSException as e:
            print(e)
            continue


insert_cur.close()
select_cur.close()
db_conn.close()

