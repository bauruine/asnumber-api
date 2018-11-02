--
-- PostgreSQL database dump
--

-- Dumped from database version 9.5.13
-- Dumped by pg_dump version 9.5.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: get_v4prefix(cidr); Type: FUNCTION; Schema: public; Owner: asnumber
--

CREATE FUNCTION public.get_v4prefix(ip cidr) RETURNS TABLE(prefix cidr, asnumber bigint)
    LANGUAGE sql
    AS $_$
  select prefix, asnumber from v4prefixes
  WHERE $1 << prefix ORDER BY prefix DESC LIMIT 1  
$_$;


ALTER FUNCTION public.get_v4prefix(ip cidr) OWNER TO asnumber;

--
-- Name: get_v6prefix(cidr); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_v6prefix(ip cidr) RETURNS TABLE(prefix cidr, asnumber bigint)
    LANGUAGE sql
    AS $_$
  select prefix, asnumber from v6prefixes
  WHERE $1 << prefix ORDER BY prefix DESC LIMIT 1
$_$;


ALTER FUNCTION public.get_v6prefix(ip cidr) OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: asnumbers; Type: TABLE; Schema: public; Owner: asnumber
--

CREATE TABLE public.asnumbers (
    asnumber bigint,
    asname character varying(255),
    asdescription character varying(255),
    country character varying(255),
    "RIR" character varying(255)
);


ALTER TABLE public.asnumbers OWNER TO asnumber;

--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: asnumber
--

CREATE TABLE public.schema_migrations (
    version character varying(255) NOT NULL
);


ALTER TABLE public.schema_migrations OWNER TO asnumber;

--
-- Name: v4prefixes; Type: TABLE; Schema: public; Owner: asnumber
--

CREATE TABLE public.v4prefixes (
    prefix cidr,
    asnumber bigint,
    "timestamp" timestamp without time zone
);


ALTER TABLE public.v4prefixes OWNER TO asnumber;

--
-- Name: v6prefixes; Type: TABLE; Schema: public; Owner: asnumber
--

CREATE TABLE public.v6prefixes (
    prefix cidr,
    asnumber bigint,
    "timestamp" timestamp without time zone
);


ALTER TABLE public.v6prefixes OWNER TO asnumber;

--
-- Name: asnumber_idx; Type: INDEX; Schema: public; Owner: asnumber
--

CREATE UNIQUE INDEX asnumber_idx ON public.asnumbers USING btree (asnumber);


--
-- Name: unique_schema_migrations; Type: INDEX; Schema: public; Owner: asnumber
--

CREATE UNIQUE INDEX unique_schema_migrations ON public.schema_migrations USING btree (version);


--
-- Name: v4asn_idx; Type: INDEX; Schema: public; Owner: asnumber
--

CREATE INDEX v4asn_idx ON public.v4prefixes USING btree (asnumber);


--
-- Name: v4prefix_idx; Type: INDEX; Schema: public; Owner: asnumber
--

CREATE INDEX v4prefix_idx ON public.v4prefixes USING gist (prefix inet_ops);


--
-- Name: v6asn_idx; Type: INDEX; Schema: public; Owner: asnumber
--

CREATE INDEX v6asn_idx ON public.v6prefixes USING btree (asnumber);


--
-- Name: v6prefix_idx; Type: INDEX; Schema: public; Owner: asnumber
--

CREATE INDEX v6prefix_idx ON public.v6prefixes USING gist (prefix inet_ops);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

