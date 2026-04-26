import polars as pl
from source_tmo_extraction import raw_df
from datetime import date
from helpers import categorise_restriction,parse_restriction


def drop_columns_not_needed(df:pl.DataFrame) -> pl.DataFrame:
    """
    this function takes a polars DataFrame and drops the columns that are not needed for the analysis
    and where columns are null or empty string

    """
    
    return df.drop([
        'pre_description', 
        'times_of_enforcement', 
        'post_description', 
        'sp_filename', 
        'sp_blockname', 
        'blockimagefile', 
        'ms_grid', 
        'tariff_code', 
        'tariff', 
        'pbp_code', 
        'pbp_tariff', 
        'zone_code', 
        'order_type_ln', 
        'restriction_ln', 
        'tariff1', 
        'tariff2',
        "msGeometry",
        "boundedBy",
    ])





def filter_by_date(df:pl.DataFrame) -> pl.DataFrame:
    """
    this function takes a polars DataFrame and filters the records based on the date_from and date_to columns
    it keeps the records where date_to is null (permanent) or date_to >= today and where date_from is null or date_from <= today

    """
    today = date.today()

    df_silver = df.filter(
        # keep where date_to is null (permanent) or date_to >= today
        (pl.col("date_to").is_null()) | (pl.col("date_to") >= today)
    ).filter(
        # keep where date_from is null or date_from <= today
        (pl.col("date_from").is_null()) | (pl.col("date_from") <= today)
    )
    print("Records before date filter:", len(clean_df))
    print(f"Records after date filter: {len(df_silver)}")
    return df_silver


def filter_by_layer(df:pl.DataFrame) -> pl.DataFrame:
    """
    this function takes a polars DataFrame and filters the records based on the layer column
    it removes the records where layer starts with morders as these are not relevant for the analysis

    """
    df_silver = df.filter(
        ~pl.col("layer").str.starts_with("morders")
    )
    return df_silver





def apply_restriction_category(df:pl.DataFrame) -> pl.DataFrame:
    """
    this function takes a polars DataFrame and applies the categorise_restriction function to the order_type and restriction columns
    it creates a new column called restriction_category that contains the category of the restriction based on the order_type and restriction columns
    """
    df_silver = df.with_columns(
        pl.struct(["order_type", "restriction"])
        .map_elements(
            lambda x: categorise_restriction(x["order_type"], x["restriction"]),
            return_dtype=pl.Utf8
        )
        .alias("restriction_category")
    )
    return df_silver





def parse_restriction_column(df:pl.DataFrame) -> pl.DataFrame:
    """
    this function takes a polars DataFrame and applies the parse_restriction function to the restriction column
    it creates new columns based on the parsed restriction data

    """
    existing_to_drop = [c for c in ["is_any_time"] if c in df.columns]
    df_silver = df.drop(existing_to_drop)

    df_silver = df_silver.with_columns(
        pl.col("restriction").map_elements(
            lambda r: parse_restriction(r) if r else parse_restriction(""),
            return_dtype=pl.Struct({
                "is_any_time":         pl.Boolean,
                "has_exceptions":      pl.Boolean,
                "is_event_day":        pl.Boolean,
                "overnight":           pl.Boolean,
                "needs_review":        pl.Boolean,
                "days_of_week":        pl.List(pl.Utf8),
                "start_time":          pl.Utf8,
                "end_time":            pl.Utf8,
                "sat_start_time":      pl.Utf8,
                "sat_end_time":        pl.Utf8,
                "time_window_2_start": pl.Utf8,
                "time_window_2_end":   pl.Utf8,
            })
        ).alias("parsed")
    ).unnest("parsed")
    return df_silver


def cleanse_tmo_silver_layer(df:pl.DataFrame) -> pl.DataFrame:
    """create a staging dataframe with the relevant cols for postgis ingestion for silver layer"""


    stg_df=df.select([
        "pm_id"
        ,"date_from"
        ,"date_to"
        ,"street_name"
        ,"restriction"
        ,"side_of_road"
        ,'restriction_category' 
        ,'is_any_time'
        ,'has_exceptions' 
        ,'is_event_day' 
        ,'overnight' 
        ,'needs_review' 
        ,'days_of_week' 
        ,'start_time' 
        ,'end_time' 
        ,'sat_start_time' 
        ,'sat_end_time' 
        ,'time_window_2_start' 
        ,'time_window_2_end'
        ,"locality"
        ,"district"
        ,"ordlocation"
        ,"ordstart"
        ,"ordfinish"
        ,"schedule"
        ,"zonecode"
        ,"charges_doc"
        ,"entry_type"
        ,"length"
        ,"side_of_road_ln"
        ,"no_of_spaces"
        ,"order_id"
        ,"order_type"
        ,"order_ref"
        ,"order_doc"
        ,"type_ref"
        ,"borough"
        ,"layer"
        ,"wkt"
    ])


    return stg_df


if __name__ == "__main__":

    clean_df = drop_columns_not_needed(raw_df)
    filter_date_clean_df = filter_by_date(clean_df)
    apply_restriction_category_df = apply_restriction_category(filter_date_clean_df)
    apply_parse_restriction_df = parse_restriction_column(apply_restriction_category_df)
    stg_tbl_df=cleanse_tmo_silver_layer(apply_parse_restriction_df)
    print(stg_tbl_df.head())



