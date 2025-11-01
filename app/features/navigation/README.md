# Навигация

## Назначение
- Обрабатывает универсальные callback-кнопки «Назад» и «Главное меню».
- Сбрасывает FSM-состояния и обеспечивает корректный возврат в интерфейсе.

## Основные обработчики
- `router.py::back_main_handler` — callback `CallbackData.BACK_MAIN`, очищает состояние и открывает главное меню.
- `router.py::back_about_handler` — callback `CallbackData.BACK_ABOUT`, показывает раздел «О боте».

## Интеграции
- Использует `get_main_menu_keyboard` и `get_about_keyboard` из `app.shared.keyboards`.
- Сброс состояния реализован через `StateFilter("*")` и `FSMContext.clear()`.

