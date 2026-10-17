

from collections.abc import Generator
from contextlib import contextmanager

import click
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


STORY = {
    "start": {
        "text": "Вы стоите на развилке в таинственном лесу. На севере виден вход в тёмную пещеру, а на юге шумит горная река.",
        "choices": {
            "north": "cave",
            "south": "river",
        },
    },
    "cave": {
        "text": "Вы входите в холодную пещеру. В глубине спит грозный дракон, охраняя сундук с сокровищами. Что делать?",
        "choices": {
            "chest": "treasure",
            "fight": "dragon",
            "leave": "start",
        },
    },
    "river": {
        "text": "Вы выходите к бурной реке. На берегу привязан плот, а чуть дальше через реку перекинут старый мост.",
        "choices": {
            "raft": "waterfall",
            "bridge": "hermit",
            "leave": "start",
        },
    },
    "treasure": {
        "text": "Вы бесшумно подкрались к сундуку, открыли его и унесли гору золота! Победа!",
        "choices": {},
    },
    "dragon": {
        "text": "Дракон проснулся от шороха и испепелил вас огненным дыханием! Поражение.",
        "choices": {},
    },
    "waterfall": {
        "text": "Бурное течение подхватило плот и разбило о скалы на водопаде! Поражение.",
        "choices": {},
    },
    "hermit": {
        "text": "Перейдя мост, вы встречаете доброго отшельника, который помог вам выбраться из леса! Победа!",
        "choices": {},
    },
}


def next_node(story: dict, current: str, choice: str) -> str:
    if current not in story:
        raise KeyError(f"неизвестная сцена: {current}")
    node = story[current]
    if choice not in node["choices"]:
        raise ValueError(f"недопустимый выбор: {choice}")
    return node["choices"][choice]


def is_ending(story: dict, node_id: str) -> bool:
    if node_id not in story:
        raise KeyError(f"неизвестная сцена: {node_id}")
    return len(story[node_id]["choices"]) == 0


def format_stat(count: int, total: int, view: str | None = None) -> str:
    percent = count / total * 100 if total else 0.0
    if view == "abs":
        return f"{count}"
    if view == "rel":
        return f"{percent:.1f}%"
    return f"{count} ({percent:.1f}%)"

class Base(DeclarativeBase):
    pass


class Progress(Base):
    
    __tablename__ = "progress"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    node_id: Mapped[str] = mapped_column()


class Ending(Base):
    __tablename__ = "endings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column()



def get_engine(db_url: str = "sqlite:///stats.db"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def get_session(db_url: str = "sqlite:///stats.db") -> Generator[Session, None, None]:
    engine = get_engine(db_url)
    with Session(engine) as session:
        yield session


def save_progress(session: Session, node_id: str) -> None:
    session.merge(Progress(id=1, node_id=node_id))
    session.commit()


def load_progress(session: Session) -> str | None:
    progress = session.get(Progress, 1)
    return progress.node_id if progress else None


def record_ending(session: Session, ending_node_id: str) -> None:
    session.add(Ending(node_id=ending_node_id))
    progress = session.get(Progress, 1)
    if progress:
        session.delete(progress)
    session.commit()


def count_endings(session: Session) -> list[tuple[str, int]]:
    stmt = (
        select(Ending.node_id, func.count(Ending.id))
        .group_by(Ending.node_id)
        .order_by(func.count(Ending.id).desc(), Ending.node_id)
    )
    return [(row[0], row[1]) for row in session.execute(stmt).all()]



@click.group()
def cli():
@cli.command()
@click.option("--new", is_flag=True, help="Начать игру заново с начала")
def play(new: bool):   
    with get_session() as session:
        current = "start"
        if not new:
            saved = load_progress(session)
            if saved and saved in STORY:
                current = saved

        while True:
            if is_ending(STORY, current):
                click.echo(STORY[current]["text"])
                record_ending(session, current)
                break

            save_progress(session, current)
            click.echo(STORY[current]["text"])
            choices = list(STORY[current]["choices"].keys())
            choice = click.prompt("Ваш выбор", type=click.Choice(choices, case_sensitive=False))
            current = next_node(STORY, current, choice)


@cli.command()
@click.option(
    "--view",
    type=click.Choice(["abs", "rel"]),
    default=None,
    help="Вид отображения: abs, rel или оба (по умолчанию)",
)
def stats(view: str | None):
    """Показать статистику достигнутых концовок."""
    with get_session() as session:
        counts = count_endings(session)
        if not counts:
            click.echo("Пока нет завершённых игр")
            return
        total = sum(count for _, count in counts)
        for node_id, count in counts:
            click.echo(f"{node_id}: {format_stat(count, total, view)}")


if __name__ == "__main__":
    cli()
