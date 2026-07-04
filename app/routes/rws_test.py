from fastapi import APIRouter, Query
import requests
from datetime import datetime, timedelta, timezone

router = APIRouter()

OBSERVATIONS_URL = (
    "https://ddapi20-waterwebservices.rijkswaterstaat.nl/"
    "ONLINEWAARNEMINGENSERVICES/OphalenWaarnemingen"
)

CATALOG_URL = (
    "https://ddapi20-waterwebservices.rijkswaterstaat.nl/"
    "METADATASERVICES/OphalenCatalogus"
)


# =========================================================
# PARAMETERS
# =========================================================

PARAMETERS = {
    "water_level": {
        "code": "WATHTE",
        "label": "Water level",
        "unit": "cm",
        "unitCode": "CMT",
        "compartment": "OW",
    },
    "water_temperature": {
        "code": "T",
        "label": "Water temperature",
        "unit": "°C",
        "unitCode": "CEL",
        "compartment": "OW",
    },
    "discharge": {
        "code": "Q",
        "label": "Discharge",
        "unit": "m3/s",
        "unitCode": "MQS",
        "compartment": "OW",
    },
    "chloride": {
        "code": "CL",
        "label": "Chloride concentration",
        "unit": "mg/L",
        "unitCode": "M1",
        "compartment": "OW",
    },
}


# =========================================================
# LOCATIONS
# =========================================================

LOCATIONS = {
    "hagestein_boven": {
        "code": "hagestein.boven",
        "label": "Hagestein, boven",
        "slug": "hagestein-boven",
        "active_parameters": [
            "water_temperature",
            "water_level",
            "discharge",
        ],
        # chloride is not currently confirmed for Hagestein, boven.
        # It can be added later if RIWA/RWS confirms availability.
    },
    "nieuwegein_lekkanaal": {
        "code": "nieuwegein.lekkanaal",
        "label": "Nieuwegein, lekkanaal",
        "slug": "nieuwegein-lekkanaal",
        "active_parameters": [
            "water_temperature",
            "water_level",
            "discharge",
            "chloride",
        ],
    },
    "nieuwegein_doorslag": {
        "code": "nieuwegein.doorslag",
        "label": "Nieuwegein, Doorslag",
        "slug": "nieuwegein-doorslag",
        "active_parameters": [
            "water_level",
            "discharge",
        ],
        # Add water_temperature/chloride later only if confirmed in the RWS catalogue.
    },
}


# =========================================================
# RWS CATALOG
# =========================================================

@router.get("/source/hard-sensors/rws/catalog")
def get_rws_catalog():
    payload = {
        "CatalogusFilter": {
            "Compartimenten": True,
            "Grootheden": True,
            "Locaties": True,
            "Parameters": True,
            "ProcesTypes": True,
        }
    }

    response = requests.post(
        CATALOG_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )

    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text[:3000]}

    return {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "url": CATALOG_URL,
        "payload_sent": payload,
        "response": data,
    }


# =========================================================
# FETCH OBSERVATIONS
# =========================================================

def fetch_rws_observations(
    location_info: dict,
    parameter_info: dict,
    days_back: int = 7,
):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back)

    payload = {
        "Locatie": {
            "Code": location_info["code"]
        },
        "AquoPlusWaarnemingMetadata": {
            "AquoMetadata": {
                "Compartiment": {
                    "Code": parameter_info["compartment"]
                },
                "Grootheid": {
                    "Code": parameter_info["code"]
                },
            }
        },
        "Periode": {
            "Begindatumtijd": start_time.strftime("%Y-%m-%dT%H:%M:%S.000+01:00"),
            "Einddatumtijd": end_time.strftime("%Y-%m-%dT%H:%M:%S.000+01:00"),
        },
    }

    response = requests.post(
        OBSERVATIONS_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text[:3000]}

    return {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "url": OBSERVATIONS_URL,
        "payload_sent": payload,
        "response": data,
    }


# =========================================================
# EXTRACT LATEST
# =========================================================

def extract_latest_measurement(response_data: dict):
    waarnemingen = response_data.get("WaarnemingenLijst", [])

    if not waarnemingen:
        return None

    measurements = waarnemingen[0].get("MetingenLijst", [])

    if not measurements:
        return None

    valid_measurements = []

    for item in measurements:
        value = item.get("Meetwaarde", {}).get("Waarde_Numeriek")
        timestamp = item.get("Tijdstip")

        if value is not None and timestamp is not None:
            valid_measurements.append(
                {
                    "latest_value": value,
                    "timestamp": timestamp,
                }
            )

    if not valid_measurements:
        return None

    return valid_measurements[-1]


# =========================================================
# EXTRACT TIMESERIES
# =========================================================

def extract_timeseries(response_data: dict):
    waarnemingen = response_data.get("WaarnemingenLijst", [])

    if not waarnemingen:
        return []

    measurements = waarnemingen[0].get("MetingenLijst", [])
    timeseries = []

    for item in measurements:
        value = item.get("Meetwaarde", {}).get("Waarde_Numeriek")
        timestamp = item.get("Tijdstip")

        if value is not None and timestamp is not None:
            timeseries.append(
                {
                    "timestamp": timestamp,
                    "value": value,
                }
            )

    return timeseries


# =========================================================
# BASIC RWS TEST ENDPOINTS
# =========================================================

@router.get("/source/hard-sensors/rws/test")
def test_rws_connection(
    location: str = Query("hagestein_boven", enum=list(LOCATIONS.keys())),
    parameter: str = Query("water_level", enum=list(PARAMETERS.keys())),
    days_back: int = Query(7, ge=1, le=365),
):
    selected_location = LOCATIONS[location]
    selected_parameter = PARAMETERS[parameter]

    result = fetch_rws_observations(
        location_info=selected_location,
        parameter_info=selected_parameter,
        days_back=days_back,
    )

    return {
        "location": selected_location,
        "parameter": selected_parameter,
        **result,
    }


@router.get("/source/hard-sensors/rws/latest")
def get_latest_rws_value(
    location: str = Query("hagestein_boven", enum=list(LOCATIONS.keys())),
    parameter: str = Query("water_temperature", enum=list(PARAMETERS.keys())),
):
    selected_location = LOCATIONS[location]
    selected_parameter = PARAMETERS[parameter]

    result = fetch_rws_observations(
        location_info=selected_location,
        parameter_info=selected_parameter,
        days_back=7,
    )

    if result["status_code"] != 200:
        return {
            "status": "error",
            "message": "RWS API request failed",
            "details": result,
        }

    latest = extract_latest_measurement(result["response"])

    if latest is None:
        return {
            "status": "no_data",
            "sensor_type": parameter,
            "location": selected_location["code"],
            "station_name": selected_location["label"],
            "message": "No measurements available",
        }

    return {
        "status": "ok",
        "sensor_type": parameter,
        "location": selected_location["code"],
        "station_name": selected_location["label"],
        "latest_value": latest["latest_value"],
        "unit": selected_parameter["unit"],
        "timestamp": latest["timestamp"],
    }


@router.get("/source/hard-sensors/rws/timeseries")
def get_rws_timeseries(
    location: str = Query("hagestein_boven", enum=list(LOCATIONS.keys())),
    parameter: str = Query("water_temperature", enum=list(PARAMETERS.keys())),
    days_back: int = Query(2, ge=1, le=30),
):
    selected_location = LOCATIONS[location]
    selected_parameter = PARAMETERS[parameter]

    result = fetch_rws_observations(
        location_info=selected_location,
        parameter_info=selected_parameter,
        days_back=days_back,
    )

    if result["status_code"] != 200:
        return {
            "status": "error",
            "message": "RWS API request failed",
            "details": result,
        }

    timeseries = extract_timeseries(result["response"])

    return {
        "status": "ok" if timeseries else "no_data",
        "sensor_type": parameter,
        "location": selected_location["code"],
        "station_name": selected_location["label"],
        "label": selected_parameter["label"],
        "unit": selected_parameter["unit"],
        "days_back": days_back,
        "count": len(timeseries),
        "timeseries": timeseries,
    }


# =========================================================
# NGSI-LD TRANSFORMATION FOR NTUA / NESSIE
# =========================================================

ATTRIBUTE_MAP = {
    "water_temperature": "waterTemperature",
    "water_level": "waterLevel",
    "discharge": "discharge",
    "chloride": "chlorideConcentration",
}


def to_ngsild_property(value, unit_code=None, observed_at=None):
    prop = {
        "type": "Property",
        "value": value,
    }

    if unit_code:
        prop["unitCode"] = unit_code

    if observed_at:
        prop["observedAt"] = observed_at

    return prop


def make_station_id(label: str):
    return (
        label
        .replace(",", "")
        .replace(" ", "")
        .replace("-", "")
    )


def make_riwa_ngsild_entity(location_key: str):
    selected_location = LOCATIONS[location_key]

    station_id = make_station_id(selected_location["label"])

    entity = {
        "id": f"urn:ngsi-ld:WaterQualityObserved:{station_id}:RWS",
        "type": "WaterQualityObserved",
        "stationName": {
            "type": "Property",
            "value": selected_location["label"],
        },
        "stationCode": {
            "type": "Property",
            "value": selected_location["code"],
        },
        "sourceProvider": {
            "type": "Property",
            "value": "Rijkswaterstaat / RIWA public data",
        },
        "module": {
            "type": "Property",
            "value": "Source Module",
        },
        "sensorCategory": {
            "type": "Property",
            "value": "Hard sensor / public data feed",
        },
        "dataStatus": {
            "type": "Property",
            "value": "live",
        },
        "servedFor": {
            "type": "Property",
            "value": "NTUA / Nessie integration",
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ],
    }

    latest_timestamps = []
    unavailable_parameters = []

    for parameter_key in selected_location["active_parameters"]:
        selected_parameter = PARAMETERS[parameter_key]
        attr_name = ATTRIBUTE_MAP[parameter_key]

        result = fetch_rws_observations(
            location_info=selected_location,
            parameter_info=selected_parameter,
            days_back=7,
        )

        if result["status_code"] != 200:
            unavailable_parameters.append(parameter_key)
            continue

        latest = extract_latest_measurement(result["response"])

        if latest is None:
            unavailable_parameters.append(parameter_key)
            continue

        latest_timestamps.append(latest["timestamp"])

        entity[attr_name] = to_ngsild_property(
            value=latest["latest_value"],
            unit_code=selected_parameter["unitCode"],
            observed_at=latest["timestamp"],
        )

    if latest_timestamps:
        entity["observedAt"] = {
            "type": "Property",
            "value": max(latest_timestamps),
        }

    entity["unavailableParameters"] = {
        "type": "Property",
        "value": unavailable_parameters,
    }

    return entity


# =========================================================
# NGSI-LD ENDPOINTS FOR NTUA / NESSIE
# =========================================================

@router.get("/source/riwa/hagestein-boven/latest")
def get_riwa_hagestein_boven_ngsild():
    return make_riwa_ngsild_entity("hagestein_boven")


@router.get("/source/riwa/nieuwegein-lekkanaal/latest")
def get_riwa_nieuwegein_lekkanaal_ngsild():
    return make_riwa_ngsild_entity("nieuwegein_lekkanaal")


@router.get("/source/riwa/nieuwegein-doorslag/latest")
def get_riwa_nieuwegein_doorslag_ngsild():
    return make_riwa_ngsild_entity("nieuwegein_doorslag")


@router.get("/source/riwa/latest")
def get_riwa_all_latest_ngsild():
    return [
        make_riwa_ngsild_entity("hagestein_boven"),
        make_riwa_ngsild_entity("nieuwegein_lekkanaal"),
        make_riwa_ngsild_entity("nieuwegein_doorslag"),
    ]


# from fastapi import APIRouter, Query
# import requests
# from datetime import datetime, timedelta

# router = APIRouter()

# OBSERVATIONS_URL = (
#     "https://ddapi20-waterwebservices.rijkswaterstaat.nl/"
#     "ONLINEWAARNEMINGENSERVICES/OphalenWaarnemingen"
# )

# CATALOG_URL = (
#     "https://ddapi20-waterwebservices.rijkswaterstaat.nl/"
#     "METADATASERVICES/OphalenCatalogus"
# )


# # =========================================================
# # PARAMETERS
# # =========================================================

# PARAMETERS = {
#     "water_level": {
#         "code": "WATHTE",
#         "label": "Water level",
#         "unit": "cm",
#         "compartment": "OW"
#     },
#     "water_temperature": {
#         "code": "T",
#         "label": "Water temperature",
#         "unit": "°C",
#         "compartment": "OW"
#     },
#     "discharge": {
#         "code": "Q",
#         "label": "Discharge",
#         "unit": "m3/s",
#         "compartment": "OW"
#     },
#     "chloride": {
#         "code": "GELDHD",
#         "label": "Electrical chloride",
#         "unit": "mS/m",
#         "compartment": "OW"
#     },
#     "turbidity": {
#         "code": "TROEBHD",
#         "label": "Turbidity",
#         "unit": "%",
#         "compartment": "OW"
#     },
#     "ph": {
#         "code": "pH",
#         "label": "pH",
#         "unit": "-",
#         "compartment": "OW"
#     },
# }


# # =========================================================
# # LOCATIONS
# # =========================================================

# LOCATIONS = {
#     "hagestein_boven": {
#         "code": "hagestein.boven",
#         "label": "Hagestein, boven"
#     },
#     "hagestein_beneden": {
#         "code": "hagestein.beneden",
#         "label": "Hagestein, beneden"
#     },
#     "nieuwegein_lekkanaal": {
#         "code": "nieuwegein.lekkanaal",
#         "label": "Nieuwegein, lekkanaal"
#     },
#     "vlissingen": {
#         "code": "vlissingen",
#         "label": "Vlissingen"
#     },
# }


# # =========================================================
# # CATALOG
# # =========================================================

# @router.get("/source/hard-sensors/rws/catalog")
# def get_rws_catalog():

#     payload = {
#         "CatalogusFilter": {
#             "Compartimenten": True,
#             "Grootheden": True,
#             "Locaties": True,
#             "Parameters": True,
#             "ProcesTypes": True
#         }
#     }

#     response = requests.post(
#         CATALOG_URL,
#         json=payload,
#         headers={"Content-Type": "application/json"},
#         timeout=60
#     )

#     try:
#         data = response.json()
#     except Exception:
#         data = {"raw_text": response.text[:3000]}

#     return {
#         "status_code": response.status_code,
#         "content_type": response.headers.get("content-type"),
#         "url": CATALOG_URL,
#         "payload_sent": payload,
#         "response": data
#     }


# # =========================================================
# # FETCH OBSERVATIONS
# # =========================================================

# def fetch_rws_observations(
#     location_info: dict,
#     parameter_info: dict,
#     days_back: int = 30
# ):

#     end_time = datetime.utcnow()
#     start_time = end_time - timedelta(days=days_back)

#     payload = {
#         "Locatie": {
#             "Code": location_info["code"]
#         },
#         "AquoPlusWaarnemingMetadata": {
#             "AquoMetadata": {
#                 "Compartiment": {
#                     "Code": parameter_info["compartment"]
#                 },
#                 "Grootheid": {
#                     "Code": parameter_info["code"]
#                 }
#             }
#         },
#         "Periode": {
#             "Begindatumtijd": start_time.strftime(
#                 "%Y-%m-%dT%H:%M:%S.000+01:00"
#             ),
#             "Einddatumtijd": end_time.strftime(
#                 "%Y-%m-%dT%H:%M:%S.000+01:00"
#             )
#         }
#     }

#     response = requests.post(
#         OBSERVATIONS_URL,
#         json=payload,
#         headers={"Content-Type": "application/json"},
#         timeout=30
#     )

#     try:
#         data = response.json()
#     except Exception:
#         data = {"raw_text": response.text[:3000]}

#     return {
#         "status_code": response.status_code,
#         "content_type": response.headers.get("content-type"),
#         "url": OBSERVATIONS_URL,
#         "payload_sent": payload,
#         "response": data
#     }


# # =========================================================
# # EXTRACT LATEST
# # =========================================================

# def extract_latest_measurement(response_data: dict):

#     waarnemingen = response_data.get("WaarnemingenLijst", [])

#     if not waarnemingen:
#         return None

#     measurements = waarnemingen[0].get("MetingenLijst", [])

#     if not measurements:
#         return None

#     latest = measurements[-1]

#     return {
#         "latest_value": latest["Meetwaarde"]["Waarde_Numeriek"],
#         "timestamp": latest["Tijdstip"]
#     }


# # =========================================================
# # EXTRACT TIMESERIES
# # =========================================================

# def extract_timeseries(response_data: dict):

#     waarnemingen = response_data.get("WaarnemingenLijst", [])

#     if not waarnemingen:
#         return []

#     measurements = waarnemingen[0].get("MetingenLijst", [])

#     timeseries = []

#     for item in measurements:

#         value = item.get("Meetwaarde", {}).get(
#             "Waarde_Numeriek"
#         )

#         timestamp = item.get("Tijdstip")

#         if value is not None and timestamp is not None:

#             timeseries.append({
#                 "timestamp": timestamp,
#                 "value": value
#             })

#     return timeseries


# # =========================================================
# # TEST ENDPOINT
# # =========================================================

# @router.get("/source/hard-sensors/rws/test")
# def test_rws_connection(
#     location: str = Query(
#         "hagestein_boven",
#         enum=list(LOCATIONS.keys())
#     ),
#     parameter: str = Query(
#         "water_level",
#         enum=list(PARAMETERS.keys())
#     ),
#     days_back: int = Query(7, ge=1, le=365)
# ):

#     selected_location = LOCATIONS[location]
#     selected_parameter = PARAMETERS[parameter]

#     result = fetch_rws_observations(
#         location_info=selected_location,
#         parameter_info=selected_parameter,
#         days_back=days_back
#     )

#     return {
#         "location": selected_location,
#         "parameter": selected_parameter,
#         **result
#     }


# # =========================================================
# # LATEST VALUE ENDPOINT
# # =========================================================

# @router.get("/source/hard-sensors/rws/latest")
# def get_latest_rws_value(
#     location: str = Query(
#         "hagestein_boven",
#         enum=list(LOCATIONS.keys())
#     ),
#     parameter: str = Query(
#         "water_temperature",
#         enum=list(PARAMETERS.keys())
#     )
# ):

#     selected_location = LOCATIONS[location]
#     selected_parameter = PARAMETERS[parameter]

#     result = fetch_rws_observations(
#         location_info=selected_location,
#         parameter_info=selected_parameter,
#         days_back=7
#     )

#     if result["status_code"] != 200:
#         return {
#             "status": "error",
#             "message": "RWS API request failed",
#             "details": result
#         }

#     latest = extract_latest_measurement(
#         result["response"]
#     )

#     if latest is None:
#         return {
#             "status": "no_data",
#             "sensor_type": parameter,
#             "location": selected_location["code"],
#             "message": "No measurements available"
#         }

#     return {
#         "sensor_type": parameter,
#         "location": selected_location["code"],
#         "latest_value": latest["latest_value"],
#         "unit": selected_parameter["unit"],
#         "timestamp": latest["timestamp"]
#     }


# # =========================================================
# # TIMESERIES ENDPOINT
# # =========================================================

# @router.get("/source/hard-sensors/rws/timeseries")
# def get_rws_timeseries(
#     location: str = Query(
#         "hagestein_boven",
#         enum=list(LOCATIONS.keys())
#     ),
#     parameter: str = Query(
#         "water_temperature",
#         enum=list(PARAMETERS.keys())
#     ),
#     days_back: int = Query(
#         2,
#         ge=1,
#         le=30
#     )
# ):

#     selected_location = LOCATIONS[location]
#     selected_parameter = PARAMETERS[parameter]

#     result = fetch_rws_observations(
#         location_info=selected_location,
#         parameter_info=selected_parameter,
#         days_back=days_back
#     )

#     if result["status_code"] != 200:
#         return {
#             "status": "error",
#             "message": "RWS API request failed",
#             "details": result
#         }

#     timeseries = extract_timeseries(
#         result["response"]
#     )

#     if not timeseries:
#         return {
#             "status": "no_data",
#             "sensor_type": parameter,
#             "location": selected_location["code"],
#             "message": "No measurements available",
#             "timeseries": []
#         }

#     return {
#         "sensor_type": parameter,
#         "location": selected_location["code"],
#         "label": selected_parameter["label"],
#         "unit": selected_parameter["unit"],
#         "days_back": days_back,
#         "count": len(timeseries),
#         "time_resolution_note": (
#             "RWS measurement frequency depends "
#             "on the station and parameter; "
#             "observed values are typically "
#             "around 10-minute intervals."
#         ),
#         "timeseries": timeseries
#     }


# #### FOR CONNECTION WITH NESSIE WE HAVE THE FOLLOWING: ####
# # =========================================================
# # NGSI-LD TRANSFORMATION FOR NTUA / NESSIE
# # =========================================================

# def to_unit_code(parameter_key: str):
#     unit_map = {
#         "water_temperature": "CEL",
#         "water_level": "CMT",
#         "discharge": "MQS",  # m3/s
#         "chloride": "MSM",
#     }
#     return unit_map.get(parameter_key, "-")


# def to_ngsild_property(value, unit_code=None, observed_at=None):
#     prop = {
#         "type": "Property",
#         "value": value
#     }

#     if unit_code:
#         prop["unitCode"] = unit_code

#     if observed_at:
#         prop["observedAt"] = observed_at

#     return prop


# def make_riwa_ngsild_entity(location_key: str):
#     selected_location = LOCATIONS[location_key]

#     parameter_keys = [
#         "water_temperature",
#         "water_level",
#         "discharge",
#         "chloride",
#     ]

#     station_id = (
#         selected_location["label"]
#         .replace(",", "")
#         .replace(" ", "")
#         .replace("-", "")
#     )

#     entity = {
#         "id": f"urn:ngsi-ld:WaterQualityObserved:{station_id}:RWS",
#         "type": "WaterQualityObserved",
#         "stationName": {
#             "type": "Property",
#             "value": selected_location["label"]
#         },
#         "stationCode": {
#             "type": "Property",
#             "value": selected_location["code"]
#         },
#         "sourceProvider": {
#             "type": "Property",
#             "value": "Rijkswaterstaat / RIWA public data"
#         },
#         "module": {
#             "type": "Property",
#             "value": "Source Module"
#         },
#         "sensorCategory": {
#             "type": "Property",
#             "value": "Hard sensor / public data feed"
#         },
#         "@context": [
#             "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
#         ]
#     }

#     latest_timestamps = []

#     for parameter_key in parameter_keys:
#         selected_parameter = PARAMETERS[parameter_key]

#         result = fetch_rws_observations(
#             location_info=selected_location,
#             parameter_info=selected_parameter,
#             days_back=7
#         )

#         if result["status_code"] != 200:
#             continue

#         latest = extract_latest_measurement(result["response"])

#         if latest is None:
#             continue

#         latest_timestamps.append(latest["timestamp"])

#         if parameter_key == "water_temperature":
#             attr_name = "waterTemperature"
#         elif parameter_key == "water_level":
#             attr_name = "waterLevel"
#         elif parameter_key == "discharge":
#             attr_name = "discharge"
#         elif parameter_key == "chloride":
#             attr_name = "electricalConductivity"
#         else:
#             attr_name = parameter_key

#         entity[attr_name] = to_ngsild_property(
#             value=latest["latest_value"],
#             unit_code=to_unit_code(parameter_key),
#             observed_at=latest["timestamp"]
#         )

#     if latest_timestamps:
#         entity["observedAt"] = {
#             "type": "Property",
#             "value": max(latest_timestamps)
#         }

#     return entity


# # =========================================================
# # NGSI-LD ENDPOINTS FOR NTUA / NESSIE
# # =========================================================

# @router.get("/source/riwa/hagestein-boven/latest")
# def get_riwa_hagestein_boven_ngsild():
#     return make_riwa_ngsild_entity("hagestein_boven")


# @router.get("/source/riwa/nieuwegein-lekkanaal/latest")
# def get_riwa_nieuwegein_lekkanaal_ngsild():
#     return make_riwa_ngsild_entity("nieuwegein_lekkanaal")


# @router.get("/source/riwa/latest")
# def get_riwa_all_latest_ngsild():
#     return [
#         make_riwa_ngsild_entity("hagestein_boven"),
#         make_riwa_ngsild_entity("nieuwegein_lekkanaal")
#     ]