"""i18n del backend: helper L() y la directiva de idioma para la IA."""

from core.i18n import L, lang_directive


def test_L_devuelve_castellano_por_defecto():
    assert L("es", "hola", "hello") == "hola"


def test_L_devuelve_ingles_con_en():
    assert L("en", "hola", "hello") == "hello"


def test_L_trata_cualquier_otro_valor_como_castellano():
    # El front nunca manda algo distinto de es/en, pero no debe romper.
    assert L("fr", "hola", "hello") == "hola"


def test_lang_directive_menciona_el_idioma():
    assert "English" in lang_directive("en")
    assert "español" in lang_directive("es").lower()
