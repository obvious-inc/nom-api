from fastapi import APIRouter

router = APIRouter()


@router.get("/", include_in_schema=False)
def get_index():
    return {"status": "ok"}
