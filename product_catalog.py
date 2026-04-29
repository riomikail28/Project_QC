from __future__ import annotations

from typing import Optional


CENTRAL_KITCHEN_PRODUCTS: list[dict] = [
    {"product_code": "SKU-BEEF-001", "product_name": "Finish Goods - Chilled/Frozen Original beef 90gr - AK", "brix_min": 11.0, "brix_max": 14.0},
    {"product_code": "SKU-BEEF-002", "product_name": "Finish Goods - Chilled/Frozen Teriyaki beef 90gr- AK", "brix_min": 11.0, "brix_max": 14.0},
    {"product_code": "SKU-CHKN-001", "product_name": "Finish Goods - Chilled/Frozen Teriyaki chicken 90gr - AK", "brix_min": 11.0, "brix_max": 14.0},
    {"product_code": "SKU-CUGIL-001", "product_name": "Finish Goods - Chilled/Frozen Cugil 100gr - AK", "brix_min": 11.0, "brix_max": 14.0},
    {"product_code": "SKU-CUGIL-002", "product_name": "Finish Goods - Chilled/Frozen Cugil tanpa Pete 100gr - AK", "brix_min": 11.0, "brix_max": 14.0},
    {"product_code": "SKU-BUMBU-001", "product_name": "Finish Goods - Bumbu Pecel 150gr - AG", "ph_min": 4.0, "ph_max": 6.0},
    {"product_code": "SKU-BUMBU-002", "product_name": "Finish Goods - Garlic In Oil 150gr - AG", "ph_min": 4.5, "ph_max": 7.0},
    {"product_code": "SKU-BUMBU-003", "product_name": "Finish Goods - Bumbu Dasar Merah 150gr - AG", "ph_min": 5.0, "ph_max": 6.5},
    {"product_code": "SKU-BUMBU-004", "product_name": "Finish Goods - Bumbu Dasar Putih 150gr - AG", "ph_min": 5.0, "ph_max": 6.5},
    {"product_code": "SKU-WIP-001", "product_name": "Finish Goods - WIP Astro Kitchen - Espresso concentrate 1L", "tds_min": 4800.0, "tds_max": 5700.0},
    {"product_code": "SKU-WIP-002", "product_name": "Finish Goods - WIP Cold Brew concentrate PATRIA 1L - AK", "tds_min": 2300.0, "tds_max": 3700.0},
    {"product_code": "SKU-WIP-003", "product_name": "Finish Goods - WIP Cold Brew concentrate KINTAMANI 1L - AK", "tds_min": 2300.0, "tds_max": 3700.0},
    {"product_code": "SKU-CHKN-002", "product_name": "Finish Goods - Grilled Chicken 100gr - AK", "brix_min": 55.0, "brix_max": 65.0, "ph_min": 4.0, "ph_max": 6.0},
    {"product_code": "SKU-EGG-001", "product_name": "Finish Goods - Telur Marinated 1pcs - AK", "brix_min": 25.0, "brix_max": 35.0},
    {"product_code": "SKU-ONIG-001", "product_name": "Finish Goods - Onigiri Salmon Mentai 110gr - AK", "ph_min": 3.5, "ph_max": 6.5},
    {"product_code": "SKU-ONIG-002", "product_name": "Finish Goods - Onigiri Tuna Mayo 110gr - AK", "ph_min": 3.5, "ph_max": 6.5},
    {"product_code": "SKU-ONIG-003", "product_name": "Finish Goods - Onigiri Ebi Mentai 110gr - AK", "ph_min": 3.0, "ph_max": 6.0},
    {"product_code": "SKU-ONIG-004", "product_name": "Finish Goods - Onigiri Beef Yakiniku 110gr - AK", "brix_min": 20.0, "brix_max": 25.0, "ph_min": 4.0, "ph_max": 6.0},
    {"product_code": "SKU-ONIG-005", "product_name": "Finish Goods - Onigiri Chicken Truffle 110gr - AK", "brix_min": 15.0, "brix_max": 25.0, "ph_min": 5.0, "ph_max": 7.0},
    {"product_code": "SKU-SAMBAL-001", "product_name": "Finish Goods - Sambal Korek 15gr ver 2 - AK", "ph_min": 4.0, "ph_max": 6.0},
    {"product_code": "SKU-SAUCE-001", "product_name": "Finish Goods - Sauce Katsu 100gr", "brix_min": 20.0, "brix_max": 30.0, "ph_min": 3.0, "ph_max": 4.0},
    {"product_code": "SKU-SAUCE-002", "product_name": "Finish Goods - Sauce Mentai 100gr", "brix_min": 35.0, "brix_max": 75.0, "ph_min": 3.0, "ph_max": 4.0},
    {"product_code": "SKU-HONEY-001", "product_name": "Finish Goods - Honey Jelly 150gr", "brix_min": 9.0, "brix_max": 11.0},
]


def product_by_code(product_code: str) -> Optional[dict]:
    return next((p for p in CENTRAL_KITCHEN_PRODUCTS if p["product_code"] == product_code), None)


def sop_params(product: dict) -> dict:
    params = {}
    for key, unit in [("brix", "%"), ("ph", "pH"), ("tds", "ppm")]:
        lo = product.get(f"{key}_min")
        hi = product.get(f"{key}_max")
        if lo is not None or hi is not None:
            params[key] = {"min": lo, "max": hi, "unit": unit}
    return params
