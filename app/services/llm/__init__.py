"""Работа с LLM: запросы и разбор игровых тегов."""

from app.services.llm.client import call_llm
from app.services.llm.effects import parse_effects

__all__ = ["call_llm", "parse_effects"]
