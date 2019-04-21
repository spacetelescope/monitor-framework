from .database_config import database, pragmas

SETTINGS = {
    'database': database
}

SETTINGS.update(pragmas)
