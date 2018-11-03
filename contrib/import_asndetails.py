import re
import yaml
import dns.resolver
import psycopg2

resolver = dns.resolver.Resolver()

# load config file
with open("../config.yml", 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)

db_conn = psycopg2.connect(dbname=cfg['psql']['dbname'], user=cfg['psql']['user'], host=cfg['psql']['host'], password=cfg['psql']['password'])

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

