import logging

from backend.qc.product_catalog import CENTRAL_KITCHEN_PRODUCTS
from backend.services.base_service import BaseService

logger = logging.getLogger("qc.services.product")


class ProductService(BaseService):
    def list_products(self):
        if not self.sb:
            return self._empty(CENTRAL_KITCHEN_PRODUCTS)
        try:
            res = (
                self.sb.table("products")
                .select(
                    "id,product_code,sku_code,product_name,description,ph_min,ph_max,brix_min,brix_max,tds_min,tds_max,is_active,created_at,updated_at"
                )
                .order("product_code")
                .execute()
            )
            products = res.data or []
            for item in products:
                if "product_code" not in item and item.get("sku_code"):
                    item["product_code"] = item["sku_code"]
            return self._empty(products)
        except Exception as exc:
            logger.warning("Product admin list failed, using local catalog: %s", exc)
            return self._empty(CENTRAL_KITCHEN_PRODUCTS)

    def create_product(self, payload):
        if not self.sb:
            return {"success": False, "detail": "Database belum terhubung"}
        try:
            try:
                res = self.sb.table("products").insert([payload]).execute()
            except Exception:
                compact_payload = {k: v for k, v in payload.items() if k != "sku_code"}
                res = self.sb.table("products").insert([compact_payload]).execute()
            return self._empty((res.data or [None])[0])
        except Exception as exc:
            logger.error("Create product failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def update_product(self, product_id, payload):
        if not self.sb:
            return {"success": False, "detail": "Database belum terhubung"}
        try:
            try:
                res = self.sb.table("products").update(payload).eq("id", product_id).execute()
            except Exception:
                compact_payload = {k: v for k, v in payload.items() if k != "sku_code"}
                res = self.sb.table("products").update(compact_payload).eq("id", product_id).execute()
            return self._empty((res.data or [None])[0])
        except Exception as exc:
            logger.error("Update product failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def delete_product(self, product_id):
        if not self.sb:
            return {"success": False, "detail": "Database belum terhubung"}
        try:
            self.sb.table("products").delete().eq("id", product_id).execute()
            return self._empty({"success": True})
        except Exception as exc:
            logger.error("Delete product failed: %s", exc)
            return {"success": False, "detail": str(exc)}
