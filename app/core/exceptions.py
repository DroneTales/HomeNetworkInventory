class ValidationError(Exception):
    """Ошибка валидации данных.

    Используется в CRUD-слое, чтобы сообщить роутеру, что данные
    не прошли проверку. Роутер ловит её и возвращает форму с ошибкой.
    """

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field

