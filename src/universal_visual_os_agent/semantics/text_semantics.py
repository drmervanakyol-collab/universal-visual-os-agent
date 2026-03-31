"""Shared Turkish-aware text normalization and matching helpers for semantics."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

_TOKEN_SPLIT_PATTERN = re.compile(r"[\s,.:;!?/\\|()\[\]{}\"'`~\-_]+")
_TURKISH_CASEFOLD_TRANSLATION = str.maketrans(
    {
        "İ": "i",
    }
)
_TURKISH_ASCII_TRANSLATION = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
)


@dataclass(slots=True, frozen=True, kw_only=True)
class TextSemanticVocabulary:
    """Pre-normalized vocabulary used for deterministic UI-text matching."""

    canonical_terms: tuple[str, ...]
    normalized_terms: frozenset[str]
    folded_terms: frozenset[str]
    canonical_by_normalized: Mapping[str, str]
    canonical_by_folded: Mapping[str, str]


def normalize_ui_text(text: str | None) -> str:
    """Normalize casing and Turkish dotted/dotless-I variants for UI text."""

    if text is None:
        return ""
    normalized = unicodedata.normalize("NFKC", text).strip()
    if not normalized:
        return ""
    casefold_ready = normalized.translate(_TURKISH_CASEFOLD_TRANSLATION)
    return " ".join(casefold_ready.casefold().split())


def tokenize_ui_text(text: str | None) -> tuple[str, ...]:
    """Split UI text into deterministic tokens for multilingual matching."""

    normalized = normalize_ui_text(text)
    if not normalized:
        return ()
    return tuple(
        token
        for token in _TOKEN_SPLIT_PATTERN.split(normalized)
        if token
    )


def normalize_ui_phrase(text: str | None) -> str:
    """Normalize UI text into a punctuation-insensitive phrase form."""

    return " ".join(tokenize_ui_text(text))


def fold_ui_phrase(text: str | None) -> str:
    """Return an accent-insensitive folded phrase for OCR-tolerant matching."""

    normalized = normalize_ui_phrase(text)
    if not normalized:
        return ""
    translated = normalized.translate(_TURKISH_ASCII_TRANSLATION)
    decomposed = unicodedata.normalize("NFKD", translated)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def build_text_semantic_vocabulary(terms: Iterable[str]) -> TextSemanticVocabulary:
    """Build a stable, normalized vocabulary from raw UI text terms."""

    canonical_terms = tuple(
        dict.fromkeys(
            normalized_term
            for term in terms
            if (normalized_term := normalize_ui_phrase(term))
        )
    )
    canonical_by_normalized: dict[str, str] = {}
    canonical_by_folded: dict[str, str] = {}
    for term in canonical_terms:
        canonical_by_normalized.setdefault(term, term)
        folded_term = fold_ui_phrase(term)
        if folded_term:
            canonical_by_folded.setdefault(folded_term, term)
    return TextSemanticVocabulary(
        canonical_terms=canonical_terms,
        normalized_terms=frozenset(canonical_terms),
        folded_terms=frozenset(canonical_by_folded),
        canonical_by_normalized=MappingProxyType(canonical_by_normalized),
        canonical_by_folded=MappingProxyType(canonical_by_folded),
    )


def phrase_matches_vocabulary(text: str | None, vocabulary: TextSemanticVocabulary) -> bool:
    """Match a normalized UI phrase against a multilingual vocabulary."""

    normalized = normalize_ui_phrase(text)
    if _phrase_matches_terms(normalized, vocabulary.normalized_terms):
        return True
    folded = fold_ui_phrase(text)
    return _phrase_matches_terms(folded, vocabulary.folded_terms)


def keyword_hits(
    texts: Iterable[str],
    vocabulary: TextSemanticVocabulary,
) -> tuple[str, ...]:
    """Return deterministic keyword hits in text order using normalized vocabularies."""

    matched_terms: list[str] = []
    for text in texts:
        for token in tokenize_ui_text(text):
            canonical_term = vocabulary.canonical_by_normalized.get(token)
            if canonical_term is None:
                canonical_term = vocabulary.canonical_by_folded.get(fold_ui_phrase(token))
            if canonical_term is not None and canonical_term not in matched_terms:
                matched_terms.append(canonical_term)
    return tuple(matched_terms)


def _phrase_matches_terms(text: str, terms: frozenset[str]) -> bool:
    if not text:
        return False
    if text in terms:
        return True
    haystack = f" {text} "
    return any(f" {term} " in haystack for term in terms)


BUTTON_TEXT_VOCABULARY = build_text_semantic_vocabulary(
    (
        "accept",
        "add",
        "apply",
        "confirm",
        "continue",
        "create",
        "delete",
        "done",
        "install",
        "launch",
        "next",
        "ok",
        "okay",
        "open",
        "remove",
        "retry",
        "save",
        "submit",
        "update",
        "aç",
        "devam",
        "ekle",
        "gönder",
        "güncelle",
        "ileri",
        "kabul et",
        "kaydet",
        "kaldır",
        "oluştur",
        "onayla",
        "sil",
        "tamam",
        "yükle",
        "yeniden dene",
    )
)
INPUT_TEXT_VOCABULARY = build_text_semantic_vocabulary(
    (
        "email",
        "e-posta",
        "eposta",
        "filter",
        "find",
        "password",
        "search",
        "search projects",
        "type",
        "type here",
        "username",
        "ara",
        "ara projeler",
        "arama",
        "buraya yaz",
        "filtre",
        "kullanıcı adı",
        "şifre",
        "yaz",
    )
)
CLOSE_TEXT_VOCABULARY = build_text_semantic_vocabulary(
    (
        "close",
        "exit",
        "quit",
        "x",
        "kapat",
        "çık",
        "çıkış",
    )
)
DISMISS_TEXT_VOCABULARY = build_text_semantic_vocabulary(
    (
        "cancel",
        "dismiss",
        "got it",
        "later",
        "maybe later",
        "no thanks",
        "not now",
        "skip",
        "anladım",
        "atla",
        "belki sonra",
        "daha sonra",
        "hayır teşekkürler",
        "iptal",
        "şimdi değil",
    )
)
NAVIGATION_TEXT_VOCABULARY = build_text_semantic_vocabulary(
    (
        "account",
        "dashboard",
        "edit",
        "file",
        "help",
        "home",
        "menu",
        "profile",
        "search",
        "settings",
        "tools",
        "view",
        "anasayfa",
        "ara",
        "arama",
        "ayarlar",
        "araçlar",
        "dashboard",
        "dosya",
        "düzenle",
        "görünüm",
        "hesap",
        "menü",
        "profil",
        "yardım",
    )
)
STATUS_TEXT_VOCABULARY = build_text_semantic_vocabulary(
    (
        "connected",
        "error",
        "failed",
        "loading",
        "offline",
        "online",
        "ready",
        "saved",
        "saving",
        "sync",
        "updated",
        "warning",
        "bağlandı",
        "bağlı",
        "başarısız",
        "çevrimdışı",
        "çevrimiçi",
        "güncellendi",
        "hazır",
        "hata",
        "kaydedildi",
        "kaydediliyor",
        "senkronize",
        "uyarı",
        "yükleniyor",
    )
)
