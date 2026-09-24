import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_path() -> None:
    """Проверяет, что папка для SQLite-файла существует.

    Если внешний диск не смонтирован, SQLite создаст файл в пустой папке
    на SD-карте, и данные «затенятся» при подключении диска.
    Лучше упасть с внятной ошибкой, чем тихо потерять базу.
    """
    url = settings.database_url
    if not url.startswith("sqlite"):
        return

    # sqlite:////abs/path/file.db -> /abs/path/file.db
    # sqlite:///./rel/path/file.db -> ./rel/path/file.db
    # sqlite:///:memory: -> пропускаем
    path_part = url.replace("sqlite:///", "", 1)

    if path_part.startswith(":memory:"):
        return

    db_path = Path(path_part).resolve()
    parent = db_path.parent

    if not parent.exists():
        raise RuntimeError(
            f"Database directory does not exist: {parent}\n"
            f"Create the directory or mount the storage device before starting."
        )

    if not os.access(parent, os.W_OK):
        raise RuntimeError(
            f"Нет прав на запись в папку БД: {parent}"
        )

