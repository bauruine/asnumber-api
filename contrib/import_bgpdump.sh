#!/bin/bash
# Update the postgresql prefix data
#
TIME=`date "+%Y-%m-%d %H:%M:%S"`
export PGPASSWORD=

base_path=/tmp

/usr/bin/wget http://data.ris.ripe.net/rrc12/latest-bview.gz -O $base_path/latest-bview.gz
/usr/local/bin/bgpdump2 -6 $base_path/latest-bview.gz | awk -F ' ' "{ print \$1 \",\" \$4 \",$TIME\" }" | sort -u > postgresqlv6.sql
psql -h 10.0.3.11 -U asnumber -d asnumber -c "\copy v6prefixes(prefix,asnumber,timestamp) FROM postgresqlv6.sql  with delimiter AS ','" && psql -h 10.0.3.11 -U asnumber -d asnumber -c "DELETE FROM v6prefixes WHERE timestamp < current_timestamp - interval '30' minute;"
/usr/local/bin/bgpdump2 -4 $base_path/latest-bview.gz | awk -F ' ' "{ print \$1 \",\" \$4 \",$TIME\" }" | grep -v '0.0.0.0/0' |sort -u > postgresqlv4.sql
psql -h 10.0.3.11 -U asnumber -d asnumber -c "\copy v4prefixes(prefix,asnumber,timestamp) FROM postgresqlv4.sql  with delimiter AS ','" && psql -h 10.0.3.11 -U asnumber -d asnumber -c "DELETE FROM v4prefixes WHERE timestamp < current_timestamp - interval '30' minute;"
$base_path/latest-bview.gz
