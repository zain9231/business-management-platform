from fastapi import APIRouter

router = APIRouter(prefix="/health")


@router.get("/live")
def read_live() -> dict[str, str]:
    return {"status": "live"}
