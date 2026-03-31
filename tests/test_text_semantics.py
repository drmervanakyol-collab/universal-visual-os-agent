from __future__ import annotations

from universal_visual_os_agent.semantics.text_semantics import (
    BUTTON_TEXT_VOCABULARY,
    CLOSE_TEXT_VOCABULARY,
    DISMISS_TEXT_VOCABULARY,
    NAVIGATION_TEXT_VOCABULARY,
    STATUS_TEXT_VOCABULARY,
    fold_ui_phrase,
    keyword_hits,
    normalize_ui_phrase,
    phrase_matches_vocabulary,
)


def test_text_semantics_normalizes_turkish_characters_safely() -> None:
    assert normalize_ui_phrase("İPTAL") == "iptal"
    assert normalize_ui_phrase("Çıkış") == "çıkış"
    assert fold_ui_phrase("Şimdi Değil") == "simdi degil"
    assert fold_ui_phrase("Güncelle Öğesi Bağlı") == "guncelle ogesi bagli"


def test_text_semantics_matches_multilingual_ui_concepts() -> None:
    assert phrase_matches_vocabulary("Kaydet", BUTTON_TEXT_VOCABULARY) is True
    assert phrase_matches_vocabulary("Save", BUTTON_TEXT_VOCABULARY) is True
    assert phrase_matches_vocabulary("Çıkış", CLOSE_TEXT_VOCABULARY) is True
    assert phrase_matches_vocabulary("Cikis", CLOSE_TEXT_VOCABULARY) is True
    assert phrase_matches_vocabulary("Şimdi Değil", DISMISS_TEXT_VOCABULARY) is True
    assert phrase_matches_vocabulary("Simdi Degil", DISMISS_TEXT_VOCABULARY) is True


def test_text_semantics_reports_keyword_hits_deterministically() -> None:
    assert keyword_hits(("Dosya Ayarlar Yardim",), NAVIGATION_TEXT_VOCABULARY) == (
        "dosya",
        "ayarlar",
        "yardım",
    )
    assert keyword_hits(("Hazir Baglandi",), STATUS_TEXT_VOCABULARY) == (
        "hazır",
        "bağlandı",
    )
