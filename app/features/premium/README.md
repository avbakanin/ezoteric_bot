# Premium-заглушки

## Назначение
- Показывает информацию о премиум-подписке и недоступных функциях.
- Позволяет быстро вернуть пользователя в главное меню после просмотра.

## Основные обработчики
- `router.py::premium_handler` — обрабатывает кнопки `PREMIUM_FULL` и `PREMIUM_COMPATIBILITY`, выводит заглушки.
- `router.py::premium_info_handler` — callback `PREMIUM_INFO`, описывает преимущества подписки.
- `router.py::subscribe_handler` — callback `SUBSCRIBE`, сообщает, что оформление будет доступно позже.

## Использование
- Все тексты берутся из `MessagesData` (раздел Premium).
- В ответах используется клавиатура `get_back_to_main_keyboard`.

