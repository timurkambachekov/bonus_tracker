from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"message": "bonus_tracker API"}


@router.get("/health")
def health():
    return {"status": "ok"}
