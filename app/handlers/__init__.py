from aiogram import Dispatcher

from handlers.affirmation import router as affirmation_router
from handlers.back import router as back_router
from handlers.compability import router as compability_router
from handlers.diary import router as diary_router
from handlers.feedback import router as feedback_router
from handlers.handlers import router as handlers_router
from handlers.life_path_number import router as life_path_number_router
from handlers.premium import router as premium_router


def setup_routers(dp: Dispatcher):
    routers = [
        handlers_router,
        diary_router,
        back_router,
        premium_router,
        feedback_router,
        compability_router,
        affirmation_router,
        life_path_number_router,
    ]

    for router in routers:
        dp.include_router(router)


__all__ = ["setup_routers"]  # явный экспорт
