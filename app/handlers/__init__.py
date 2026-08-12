from aiogram import Router

from . import digest, edit, tasks

router = Router()
router.include_router(tasks.router)
router.include_router(edit.router)
router.include_router(digest.router)
