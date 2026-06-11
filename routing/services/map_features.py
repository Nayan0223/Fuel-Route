def build_map_feature_collection(
    route_geometry: dict,
    route_properties: dict,
    start: tuple[float, float],
    finish: tuple[float, float],
    fuel_stops: list[dict],
) -> dict:
    features = [
        {
            "type": "Feature",
            "geometry": route_geometry,
            "properties": {
                "kind": "route",
                **route_properties,
            },
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [start[1], start[0]],
            },
            "properties": {"kind": "start"},
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [finish[1], finish[0]],
            },
            "properties": {"kind": "finish"},
        },
    ]

    for index, stop in enumerate(fuel_stops, start=1):
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [stop["longitude"], stop["latitude"]],
                },
                "properties": {
                    "kind": "fuel_stop",
                    "stop_number": index,
                    **stop,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
