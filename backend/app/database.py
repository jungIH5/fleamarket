import os
import time

from sqlalchemy.exc import OperationalError
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./layout.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db(retries: int = 10, delay: float = 2.0) -> None:
    """docker-compose로 DB 컨테이너와 동시에 기동될 때 접속 준비가 안 됐을 수 있어 재시도한다."""
    for attempt in range(retries):
        try:
            SQLModel.metadata.create_all(engine)
            return
        except OperationalError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


def get_session():
    with Session(engine) as session:
        yield session
