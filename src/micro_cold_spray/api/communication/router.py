from fastapi import APIRouter
from .endpoints import tags, motion, equipment

router = APIRouter(prefix="/communication")
router.include_router(tags.router)
router.include_router(motion.router)
router.include_router(equipment.router)
