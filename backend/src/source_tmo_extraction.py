import html
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
import pandas as pd
import requests
import json
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
def extract_traffic_orders():

    """
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

    append the record dict to all_features list which will be used to create a DataFrame at the end


    """
    BASE_WFS = "https://mapserver.traffweb.app/cgi-bin/hounslow/parkmap" 
    url="https://hounslow.traffweb.app/traffweb/1/TrafficOrders"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    response = requests.request("GET",url,headers=headers,timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    layer_input = soup.find("input", {"id": "layerconfig"})

    if layer_input:
        raw = html.unescape(layer_input.get("value", ""))
        # print(f"this is the layerinput{raw}")
        layers = json.loads(raw)
        layer_id_map={
            layer["name"]: layer["defsel"]
            for layer in layers
            if layer["defsel"]
        }
        # print(layer_id_map)
    all_features = []

    for layer_name, order_ids in layer_id_map.items():

        
        if layer_name == "signs":
            print(f"  Skipping {layer_name}")
            continue

        print(f"Fetching {layer_name}...")

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
            print(f"  Skipping — status {wfs_response.status_code}")
            continue


        try:
            root = ET.fromstring(wfs_response.text)

            ns = {
                "wfs": "http://www.opengis.net/wfs",
                "gml": "http://www.opengis.net/gml",
                "ms":  "http://mapserver.gis.umn.edu/mapserver",
            }

            # Correct path — through gml:featureMember
            features = root.findall(f"gml:featureMember/ms:{layer_name}", ns)
            print(f"  Features found: {len(features)}")

            for feature in features:
                record = {"layer": layer_name, "borough": "hounslow"}
                for child in feature:
                    tag= child.tag.split("}")[-1]
                    record[tag] = child.text
                    if tag=="msGeometry":
                        coords_elem=child.find(".//gml:coordinates",ns)
                        if coords_elem is not None and coords_elem.text:
                            raw=coords_elem.text.strip()
                            record["geom_raw"]=raw
                            record["geom_srid"]=27700

                            pairs=raw.split()
                            wkt_coords=", ".join(
                                f"{p.split(',')[0]} {p.split(',')[1]}"
                                for p in pairs if "," in p
                            )
                            record["wkt"]=f"LINESTRING ({wkt_coords})"
                        else:
                            record["geom_raw"]=None
                            record["geom_srid"]=None
                            record["wkt"]=None
                            
                all_features.append(record)

    
        except ET.ParseError as e:
            print(f"  Parse error: {e}")
    
    df = pd.DataFrame(all_features)
    return df


df = extract_traffic_orders()