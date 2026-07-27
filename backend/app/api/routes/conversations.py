from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def conversations_status() -> dict[str, str]:
    return {"status": "scaffolded"}
