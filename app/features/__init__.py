"""Регистрация feature-роутеров."""

from aiogram import Dispatcher

from .admin.router import router as admin_router
from .affirmation.router import router as affirmation_router
from .aspect_of_day.router import router as aspect_of_day_router
from .astro_forecast.router import router as astro_forecast_router
from .astro_profile.router import router as astro_profile_router
from .base.router import router as base_router
from .compatibility.router import router as compatibility_router
from .daily_number.router import router as daily_number_router
from .diary.router import router as diary_router
from .feedback.router import router as feedback_router
from .life_path.router import router as life_path_router
from .name_number.router import router as name_number_router
from .navigation.router import router as navigation_router
from .premium.router import router as premium_router
from .profile.router import router as profile_router
from .retro_alerts.router import router as retro_alerts_router
from .yes_no.router import router as yes_no_router


def setup_routers(dp: Dispatcher) -> None:
    routers = [
        admin_router,
        navigation_router,
        profile_router,
        astro_profile_router,
        aspect_of_day_router,
        astro_forecast_router,
        retro_alerts_router,
        diary_router,
        feedback_router,
        compatibility_router,
        affirmation_router,
        life_path_router,
        name_number_router,
        yes_no_router,
        daily_number_router,
        premium_router,
        base_router,
    ]

    for router in routers:
        dp.include_router(router)


__all__ = ["setup_routers"]

