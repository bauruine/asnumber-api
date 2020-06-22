CREATE TABLE asnumbers (
    asnumber bigint PRIMARY KEY,
    asname character varying(255),
    asdescription character varying(255),
    country character varying(255),
    rir character varying(255),
    last_updated timestamp without time zone
);


CREATE TABLE prefixes (
    prefix cidr PRIMARY KEY,
    added_timestamp timestamp without time zone
);


CREATE TABLE asnumbers_prefixes (
	asnumber bigint REFERENCES asnumbers(asnumber) ON UPDATE CASCADE,
	prefix cidr REFERENCES prefixes(prefix) ON UPDATE CASCADE ON DELETE CASCADE,
	first_seen timestamp without time zone,
	last_seen timestamp without time zone, 
	CONSTRAINT asnumber_prefix_primary_key PRIMARY KEY (asnumber, prefix)

);

CREATE UNIQUE INDEX asnumber_idx ON asnumbers USING btree (asnumber);
CREATE UNIQUE INDEX prefixes_idx ON prefixes USING btree (prefix);


CREATE INDEX prefix_idx ON prefixes USING gist (prefix inet_ops);


ALTER TABLE public.asnumbers OWNER TO asnumber;

ALTER TABLE public.asnumbers_prefixes OWNER TO asnumber;

ALTER TABLE public.prefixes OWNER TO asnumber;
