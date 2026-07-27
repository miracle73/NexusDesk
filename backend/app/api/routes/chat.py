from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def chat_status() -> dict[str, str]:
    return {"status": "scaffolded"}
