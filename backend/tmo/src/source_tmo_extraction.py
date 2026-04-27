import html
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
import polars as pl
import requests
import json
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def extract_all_boroughs()-> pl.DataFrame:
    """
    for each borough in the static list of boroughs with known subdomains:
    
    BASE_WFS is the endpoint for the web feature service that provides the traffic order data in GML format
    url is the URL for the webpage that contains the layer configuration for the traffic orders
    headers is a dictionary that sets the User-Agent header for the HTTP request to mimic a browser
    soup is a BeautifulSoup object that parses the HTML content of the response from the URL

    layer input is a list of dict objects that contains layer configuration information ie the layername and orderIDS
    defel is the key in the layer config that contains the orderIDs for that layer 

    load the layer into json and create a mapping of the layer name to the OrderIDs for that layer

    loop over the layer_id_map to get key value pairs of layer name and orderIDs

    skips layer name signs as it is not relevant to the traffic orders

    for each layer it makes a WTS request get the features for that layer 

    ET.fromstring is used to parse the GML response into an XML tree structure for further processing

    features are extracted from XML tree using correct path through GML featureMember elements

    loop over the features another for loop over feature to extract child elements 

    using the tag and split the tag to get actual tag name for cols heading 

    using the text of the child element as the value for that column in the record dict

    to get the geom look into msGeometry tag then into gml:coordinates as its nested 
    and extract the raw coordinates text

    create a raw geom col with raw coordinates 

    create a geom_srid col with the SRID for the coordinates

    create a wkt col by converting the raw coordinates into WKT format

    for geometry type detection:
        if 1 pair of coordinates it is a Point
        if 2 pairs of coordinates it is a LineString
        if more than 2 pairs of coordinates check if first and last coordinate are the same
            if they are the same it is a Polygon (closed ring)
            if they are not the same it is a LineString (open ring)

    append the record dict to all_features list which will be used to create a DataFrame at the end
    """

    
    STATIC_BOROUGHS = {
    "barking_dagenham": "barking-dagenham",
    "barnet":           "barnet",
    "camden":           "camden",
    "enfield":          "enfield",
    "hackney":          "hackney",
    "hounslow":         "hounslow",
    "lewisham":         "lewisham",
    "redbridge":        "redbridge",
}
    all_features = []
    
    for borough_key, subdomain in STATIC_BOROUGHS.items():
        BASE_WFS = f"https://mapserver.traffweb.app/cgi-bin/{subdomain}/parkmap"
        url = f"https://{subdomain}.traffweb.app/traffweb/1/TrafficOrders"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        print(f"\n=== {borough_key.upper()} ===")

        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        layer_input = soup.find("input", {"id": "layerconfig"})

        if not layer_input:
            print(f"  No layerconfig found — skipping")
            continue

        raw = html.unescape(layer_input.get("value", ""))
        layers = json.loads(raw)
        layer_id_map = {
            layer["name"]: layer["defsel"]
            for layer in layers
            if layer["defsel"]
        }

        for layer_name, order_ids in layer_id_map.items():
            if layer_name == "signs":
                print(f"  Skipping {layer_name}")
                continue

            print(f"  Fetching {layer_name}...")

            params = {
                "SERVICE": "WFS",
                "VERSION": "1.1.0",
                "REQUEST": "GetFeature",
                "TYPENAME": layer_name,
                "OUTPUTFORMAT": "GML2",
                "SRSNAME": "EPSG:27700",
                "MYORDERS": order_ids,
            }

            wfs_response = requests.get(BASE_WFS, params=params, timeout=120)

            if wfs_response.status_code != 200:
                print(f"    Skipping — status {wfs_response.status_code}")
                continue

            try:
                root = ET.fromstring(wfs_response.text)
                ns = {
                    "wfs": "http://www.opengis.net/wfs",
                    "gml": "http://www.opengis.net/gml",
                    "ms":  "http://mapserver.gis.umn.edu/mapserver",
                }

                features = root.findall(f"gml:featureMember/ms:{layer_name}", ns)
                print(f"    Features found: {len(features)}")

                for feature in features:
                    record = {"layer": layer_name, "borough": borough_key}

                    for child in feature:
                        tag = child.tag.split("}")[-1]
                        record[tag] = child.text

                        if tag == "msGeometry":
                            coords_elem = child.find(".//gml:coordinates", ns)
                            if coords_elem is not None and coords_elem.text:
                                raw = coords_elem.text.strip()
                                record["geom_raw"] = raw
                                record["geom_srid"] = 27700
                                pairs = raw.split()

                                if len(pairs) == 1:
                                    x, y = pairs[0].split(",")
                                    record["wkt"] = f"POINT ({x} {y})"
                                    record["geom_type"] = "Point"
                                elif len(pairs) == 2:
                                    wkt_coords = ", ".join(
                                        f"{p.split(',')[0]} {p.split(',')[1]}"
                                        for p in pairs
                                    )
                                    record["wkt"] = f"LINESTRING ({wkt_coords})"
                                    record["geom_type"] = "LineString"
                                elif len(pairs) > 2:
                                    wkt_coords = ", ".join(
                                        f"{p.split(',')[0]} {p.split(',')[1]}"
                                        for p in pairs
                                    )
                                    first, last = pairs[0], pairs[-1]
                                    if first == last:
                                        record["wkt"] = f"POLYGON (({wkt_coords}))"
                                        record["geom_type"] = "Polygon"
                                    else:
                                        record["wkt"] = f"LINESTRING ({wkt_coords})"
                                        record["geom_type"] = "LineString"
                            else:
                                record["geom_raw"] = None
                                record["geom_srid"] = None
                                record["wkt"] = None
                                record["geom_type"] = None

                    all_features.append(record)

            except ET.ParseError as e:
                print(f"    Parse error: {e}")

    return pl.DataFrame(all_features,infer_schema_length=None)


df_traffweb = extract_all_boroughs()
print(f"\nTotal features: {df_traffweb.shape}")

def correct_dtypes(df:pl.DataFrame) -> pl.DataFrame:
    """
    this function takes a polars DataFrame and corrects the data types
    it converts the date_from and date_to columns to datetime format

    """
    return df.with_columns(
    pl.col("date_from").str.strptime(pl.Date, "%Y-%m-%d"),
    pl.col("date_to").str.strptime(pl.Date, "%Y-%m-%d")
    )

raw_df= correct_dtypes(df_traffweb)

