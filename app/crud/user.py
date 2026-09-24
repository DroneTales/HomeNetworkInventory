from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.security import hash_password
from app.models.user import User

# Допустимые роли
ROLE_ADMIN = "admin"
ROLE_USER = "user"
VALID_ROLES = {ROLE_ADMIN, ROLE_USER}


def list_all(db: Session) -> list[User]:
    return db.query(User).order_by(User.username).all()


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def _validate_username(username: str) -> str:
    username = (username or "").strip()
    if not username:
        raise ValidationError("Username is required", field="username")
    if len(username) < 3:
        raise ValidationError("Username must be at least 3 characters", field="username")
    if len(username) > 100:
        raise ValidationError("Username must be at most 100 characters", field="username")
    return username


def _validate_password(password: str) -> None:
    if password is None or len(password) < 1:
        raise ValidationError("Password is required", field="password")
    # Минимум 5 символов — предупреждение, а не запрет.
    # Здесь мы не бросаем ошибку, только даём сигнал через возвращаемое значение.
    # Реальная логика предупреждения — в роутере.


def _validate_flags(
    role: str,
    can_edit: bool,
    can_view_passwords: bool,
    can_change_passwords: bool,
) -> None:
    """Проверяет комбинации флагов.

    Запрещённые комбинации:
    - can_change_passwords=True при can_edit=False (менять пароль без права менять данные)
    - can_change_passwords=True при can_view_passwords=False (менять то, чего не видишь)
    """
    if role == ROLE_ADMIN:
        return

    if can_change_passwords and not can_edit:
        raise ValidationError(
            "Cannot allow changing passwords without edit permission",
            field="can_change_passwords",
        )

    if can_change_passwords and not can_view_passwords:
        raise ValidationError(
            "Cannot allow changing passwords without viewing passwords",
            field="can_change_passwords",
        )


def create(
    db: Session,
    username: str,
    password: str,
    role: str = ROLE_USER,
    can_edit: bool = False,
    can_view_passwords: bool = False,
    can_change_passwords: bool = False,
    must_change_password: bool = False,
    is_active: bool = True,
    language: str = "en",
    theme: str = "auto",
) -> User:
    username = _validate_username(username)
    _validate_password(password)

    if role not in VALID_ROLES:
        raise ValidationError(f"Invalid role: {role}", field="role")

    if get_by_username(db, username) is not None:
        raise ValidationError(f"Username '{username}' already exists", field="username")

    _validate_flags(role, can_edit, can_view_passwords, can_change_passwords)

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        can_edit=can_edit,
        can_view_passwords=can_view_passwords,
        can_change_passwords=can_change_passwords,
        must_change_password=must_change_password,
        is_active=is_active,
        language=language,
        theme=theme,
    )
    db.add(user)
    db.flush()
    return user


def update(
    db: Session,
    user_id: int,
    username: str,
    role: str,
    can_edit: bool,
    can_view_passwords: bool,
    can_change_passwords: bool,
    is_active: bool = True,
    language: str = "en",
    theme: str = "auto",
) -> User:
    user = get_by_id(db, user_id)
    if user is None:
        raise ValidationError("User not found", field="id")

    username = _validate_username(username)

    if role not in VALID_ROLES:
        raise ValidationError(f"Invalid role: {role}", field="role")

    existing = get_by_username(db, username)
    if existing is not None and existing.id != user_id:
        raise ValidationError(f"Username '{username}' already exists", field="username")

    _validate_flags(role, can_edit, can_view_passwords, can_change_passwords)

    user.username = username
    user.role = role
    user.can_edit = can_edit
    user.can_view_passwords = can_view_passwords
    user.can_change_passwords = can_change_passwords
    user.is_active = is_active
    user.language = language
    user.theme = theme
    db.flush()
    return user


def reset_password(
    db: Session,
    user_id: int,
    new_password: str,
    must_change_password: bool = True,
) -> User:
    user = get_by_id(db, user_id)
    if user is None:
        raise ValidationError("User not found", field="id")

    if not new_password or len(new_password) < 1:
        raise ValidationError("Password is required", field="password")

    user.password_hash = hash_password(new_password)
    user.must_change_password = must_change_password
    db.flush()
    return user


def change_own_password(db: Session, user_id: int, old_password: str, new_password: str) -> User:
    from app.core.security import verify_password

    user = get_by_id(db, user_id)
    if user is None:
        raise ValidationError("User not found", field="id")

    if not verify_password(old_password, user.password_hash):
        raise ValidationError("Current password is incorrect", field="old_password")

    if not new_password or len(new_password) < 1:
        raise ValidationError("New password is required", field="new_password")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.flush()
    return user


def update_preferences(
    db: Session,
    user_id: int,
    language: str,
    theme: str,
) -> User:
    user = get_by_id(db, user_id)
    if user is None:
        raise ValidationError("User not found", field="id")

    if language not in ("en", "ru"):
        raise ValidationError(f"Unsupported language: {language}", field="language")

    if theme not in ("auto", "light", "dark"):
        raise ValidationError(f"Unsupported theme: {theme}", field="theme")

    user.language = language
    user.theme = theme
    db.flush()
    return user


def delete(db: Session, user_id: int) -> None:
    user = get_by_id(db, user_id)
    if user is None:
        raise ValidationError("User not found", field="id")

    if user.username == "Admin":
        raise ValidationError("The default Admin user cannot be deleted", field="id")

    db.delete(user)
    db.flush()

