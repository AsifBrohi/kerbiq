"""-- Table: raw_tmo.trafficorders_london

-- DROP TABLE IF EXISTS raw_tmo.trafficorders_london;

CREATE TABLE IF NOT EXISTS raw_tmo.trafficorders_london
(
    pm_id bigint NOT NULL,
    layer character varying(8) COLLATE pg_catalog."default",
    borough character varying(16) COLLATE pg_catalog."default",
    "boundedBy" character varying(10) COLLATE pg_catalog."default",
    "msGeometry" character varying(9) COLLATE pg_catalog."default",
    item_ref bigint,
    order_ref character varying(38) COLLATE pg_catalog."default",
    order_type character varying(254) COLLATE pg_catalog."default",
    street_name character varying(254) COLLATE pg_catalog."default",
    side_of_road character varying(50) COLLATE pg_catalog."default",
    locality character varying(100) COLLATE pg_catalog."default",
    district character varying(100) COLLATE pg_catalog."default",
    ordstart character varying(300) COLLATE pg_catalog."default",
    ordfinish character varying(300) COLLATE pg_catalog."default",
    ordlocation character varying(300) COLLATE pg_catalog."default",
    schedule character varying(12) COLLATE pg_catalog."default",
    date_from date,
    date_to date,
    pre_description character varying(254) COLLATE pg_catalog."default",
    times_of_enforcement character varying(50) COLLATE pg_catalog."default",
    post_description character varying(254) COLLATE pg_catalog."default",
    sp_filename character varying(20) COLLATE pg_catalog."default",
    sp_blockname character varying COLLATE pg_catalog."default",
    entry_type character varying COLLATE pg_catalog."default",
    restriction character varying COLLATE pg_catalog."default",
    order_id bigint,
    order_doc character varying COLLATE pg_catalog."default",
    blockimagefile character varying COLLATE pg_catalog."default",
    ms_grid character varying COLLATE pg_catalog."default",
    type_ref bigint,
    no_of_spaces bigint,
    length double precision,
    tariff_code bigint,
    tariff character varying(300) COLLATE pg_catalog."default",
    pbp_code bigint,
    pbp_tariff character varying(20) COLLATE pg_catalog."default",
    zone_code character varying(30) COLLATE pg_catalog."default",
    order_type_ln character varying(20) COLLATE pg_catalog."default",
    side_of_road_ln character varying(100) COLLATE pg_catalog."default",
    restriction_ln character varying(20) COLLATE pg_catalog."default",
    tariff1 character varying(254) COLLATE pg_catalog."default",
    tariff2 character varying(20) COLLATE pg_catalog."default",
    poly_id bigint,
    polyname character varying(254) COLLATE pg_catalog."default",
    poly_info character varying(30) COLLATE pg_catalog."default",
    zonecode character varying(20) COLLATE pg_catalog."default",
    charges_doc character varying(30) COLLATE pg_catalog."default",
    geom_raw character varying(5000) COLLATE pg_catalog."default",
    geom_srid bigint,
    geom_type character varying(50) COLLATE pg_catalog."default",
    wkt character varying(6000) COLLATE pg_catalog."default",
    geom geometry,
    CONSTRAINT trafficorders_london_pkey PRIMARY KEY (pm_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS raw_tmo.trafficorders_london
    OWNER to "KerbIntelligence";

GRANT ALL ON TABLE raw_tmo.trafficorders_london TO "KerbIntelligence";

CREATE INDEX IF NOT EXISTS trafficorders_london_idx_geom 
    ON raw_tmo.trafficorders_london USING GIST (geom);

"""