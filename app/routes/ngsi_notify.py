from fastapi import APIRouter, Request
from app.services.ngsi import upsert_entity, softsensor_entity


router = APIRouter()

@router.post("/ngsi-ld/notify")
async def ngsi_notify(req: Request):
    body = await req.json()
    items = body.get("data", [])
    # Minimal demo: derive a toy prediction from incoming raw turbidity
    for e in items:
        plant_obj = e.get("plant", {}).get("object", "urn:ngsi-ld:Plant:Leiduin")
        plant = plant_obj.split(":")[-1]
        current = e.get("turbidityNTU", {}).get("value")
        if current is not None:
            y_hat = float(current) * 0.9  # placeholder model logic
            await upsert_entity(softsensor_entity(plant, y_hat))
    return {"received": len(items)}
