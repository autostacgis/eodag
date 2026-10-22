"""STAC-first metadata export for AutoSTACGIS, without product acquisition.

Rules map provider metadata to asset state explicitly. Unknown state is not guessed
from a filename or an ambiguous processing-level label.
"""

from copy import deepcopy
from urllib.parse import urlsplit

EXTENSIONS = {
    "eo:": "https://stac-extensions.github.io/eo/v2.0.0/schema.json",
    "raster:": "https://stac-extensions.github.io/raster/v2.0.0/schema.json",
    "proj:": "https://stac-extensions.github.io/projection/v2.1.0/schema.json",
    "view:": "https://stac-extensions.github.io/view/v1.1.0/schema.json",
    "processing:": "https://stac-extensions.github.io/processing/v1.2.0/schema.json",
    "product:": "https://stac-extensions.github.io/product/v1.1.0/schema.json",
    "cf:": "https://stac-extensions.github.io/cf/v1.0.0/schema.json",
    "sar:": "https://stac-extensions.github.io/sar/v1.3.2/schema.json",
    "classification:": "https://stac-extensions.github.io/classification/v2.0.0/schema.json",
    "data_state:": "https://autostacgis.github.io/stac-data-state/v1.0.0/schema.json",
}

EXTENSIONS.update(
    {
        "sat:": "https://stac-extensions.github.io/sat/v1.2.0/schema.json",
        "grid:": "https://stac-extensions.github.io/grid/v1.1.0/schema.json",
    }
)


def describe_product(product, state_rules=()):
    item = deepcopy(product.as_dict())
    for rule in state_rules:
        if not all(
            item.get("properties", {}).get(k) == v
            for k, v in rule.get("when", {}).items()
        ):
            continue
        selected = rule.get("assets", [])
        if not selected:
            raise ValueError("State rules must explicitly select asset names")
        for name in selected:
            if name not in item["assets"]:
                raise ValueError(f"Unknown product asset {name}")
            for key, value in rule["set"].items():
                previous = item["assets"][name].get(key)
                if previous is not None and previous != value:
                    raise ValueError(f"Conflicting product state: {name}.{key}")
                item["assets"][name][key] = deepcopy(value)

    def prefixes(value):
        found = set()
        if isinstance(value, dict):
            for key, child in value.items():
                found.update(prefix for prefix in EXTENSIONS if key.startswith(prefix))
                found.update(prefixes(child))
        elif isinstance(value, list):
            for child in value:
                found.update(prefixes(child))
        return found

    used = prefixes(item.get("properties", {})) | prefixes(item.get("assets", {}))
    declared = item.setdefault("stac_extensions", [])

    def family(uri):
        parsed = urlsplit(uri)
        return parsed.netloc, parsed.path.rsplit("/v", 1)[0]

    families = {family(uri) for uri in declared}
    for prefix, uri in EXTENSIONS.items():
        if prefix in used and family(uri) not in families:
            declared.append(uri)
    return item
