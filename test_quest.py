import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from quest import (
    STORY,
    Base,
    cli,
    count_endings,
    format_stat,
    is_ending,
    load_progress,
    next_node,
    record_ending,
    save_progress,
)


def test_story_graph_integrity():
    """Все переходы из choices ведут в реально существующие сцены STORY."""
    assert "start" in STORY
    for node_id, node in STORY.items():
        assert "text" in node and isinstance(node["text"], str)
        assert "choices" in node and isinstance(node["choices"], dict)
        for choice, target_node in node["choices"].items():
            assert target_node in STORY, (
                f"В сцене '{node_id}' выбор '{choice}' ведет в несуществующую сцену '{target_node}'"
            )


def test_next_node_success():
    """Успешный переход по допустимому действию."""
    assert next_node(STORY, "start", "north") == "cave"
    assert next_node(STORY, "start", "south") == "river"
    assert next_node(STORY, "cave", "chest") == "treasure"
    assert next_node(STORY, "cave", "leave") == "start"


def test_next_node_invalid_choice_raises_value_error():
    """Недопустимый выбор вызывает ValueError с понятным сообщением."""
    with pytest.raises(ValueError, match="недопустимый выбор: teleport"):
        next_node(STORY, "start", "teleport")


def test_next_node_unknown_scene_raises_key_error():
    """Попытка перехода из несуществующей сцены вызывает KeyError."""
    with pytest.raises(KeyError, match="неизвестная сцена: nonexistent"):
        next_node(STORY, "nonexistent", "north")


def test_is_ending():
    """Корректное определение концовок и промежуточных сцен."""
   
    assert is_ending(STORY, "start") is False
    assert is_ending(STORY, "cave") is False
    assert is_ending(STORY, "river") is False

    assert is_ending(STORY, "treasure") is True
    assert is_ending(STORY, "dragon") is True
    assert is_ending(STORY, "waterfall") is True
    assert is_ending(STORY, "hermit") is True


def test_format_stat():
    """Форматирование статистики в режимах abs, rel и обоих (None)."""
    assert format_stat(5, 8, "abs") == "5"
    assert format_stat(5, 8, "rel") == "62.5%"
    assert format_stat(5, 8, None) == "5 (62.5%)"

    assert format_stat(3, 8, "abs") == "3"
    assert format_stat(3, 8, "rel") == "37.5%"
    assert format_stat(3, 8, None) == "3 (37.5%)"

    assert format_stat(0, 0, "abs") == "0"
    assert format_stat(0, 0, "rel") == "0.0%"
    assert format_stat(0, 0, None) == "0 (0.0%)"


def test_load_progress_initially_empty(session):
    assert load_progress(session) is None


def test_save_and_load_progress(session):
    save_progress(session, "cave")
    assert load_progress(session) == "cave"


def test_save_progress_overwrites_existing(session):
    save_progress(session, "cave")
    assert load_progress(session) == "cave"

    save_progress(session, "river")
    assert load_progress(session) == "river"


def test_record_ending_clears_progress_and_stores_ending(session):
    """Достижение концовки записывает её в endings и удаляет текущий прогресс."""
    save_progress(session, "cave")
    assert load_progress(session) == "cave"

    record_ending(session, "treasure")
    assert load_progress(session) is None

    counts = count_endings(session)
    assert counts == [("treasure", 1)]


def test_count_endings_aggregation(session):
    record_ending(session, "treasure")
    record_ending(session, "dragon")
    record_ending(session, "treasure")
    record_ending(session, "treasure")
    record_ending(session, "dragon")

    counts = count_endings(session)
    assert counts == [("treasure", 3), ("dragon", 2)]