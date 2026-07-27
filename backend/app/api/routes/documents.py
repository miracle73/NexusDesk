from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def documents_status() -> dict[str, str]:
    return {"status": "scaffolded"}
