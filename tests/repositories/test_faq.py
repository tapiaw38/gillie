"""FAQ storage: the `faqs.skill.md` round trip.

Rewritten against where FAQs actually live. The previous version imported
`src.adapters.datasources.repositories.faq.repository`, a Mongo-backed
repository that no longer exists — FAQs moved to a Markdown skill file managed
by `SkillManager`, which is what every use case under `use_cases/memory` calls
today. The stale import aborted collection for the whole suite, so nothing in
`tests/` ran under a bare `pytest`.

`no_sql_faqs_client` is still threaded through `Datasources`, but nothing
reads it any more; the file is the store.
"""

import pytest

from src.core.platform.managers.skill_manager import SkillManager


@pytest.fixture
def skills(tmp_path):
    """A manager over an empty directory, so each test owns its own file."""
    return SkillManager(memory_dir=tmp_path)


def test_a_fresh_store_has_no_faqs(skills):
    assert skills.get_faqs() == []


def test_an_added_faq_comes_back_with_its_fields(skills):
    faq_id = skills.add_faq("¿Cómo pido un reembolso?", "Escribinos y lo tramitamos.")

    stored = skills.get_faqs()

    assert len(stored) == 1
    assert stored[0]["id"] == faq_id
    assert stored[0]["question"] == "¿Cómo pido un reembolso?"
    assert stored[0]["answer"] == "Escribinos y lo tramitamos."


def test_the_category_defaults_when_none_is_given(skills):
    skills.add_faq("P", "R")

    assert skills.get_faqs()[0]["category"] == "General"


def test_a_given_category_is_kept(skills):
    skills.add_faq("P", "R", category="Envíos")

    assert skills.get_faqs()[0]["category"] == "Envíos"


def test_each_faq_gets_its_own_id(skills):
    """Blocks are found by id for update and delete, so a collision would make
    one FAQ's edit land on another's text."""
    first = skills.add_faq("P1", "R1")
    second = skills.add_faq("P2", "R2")

    assert first != second
    assert {f["id"] for f in skills.get_faqs()} == {first, second}


def test_updating_rewrites_only_the_one_block(skills):
    first = skills.add_faq("P1", "R1", category="Uno")
    second = skills.add_faq("P2", "R2", category="Dos")

    assert skills.update_faq(second, "P2 nueva", "R2 nueva") is True

    by_id = {f["id"]: f for f in skills.get_faqs()}
    assert by_id[second]["question"] == "P2 nueva"
    assert by_id[second]["answer"] == "R2 nueva"
    assert by_id[first]["question"] == "P1"
    assert by_id[first]["answer"] == "R1"


def test_updating_keeps_the_category_when_none_is_passed(skills):
    faq_id = skills.add_faq("P", "R", category="Envíos")

    skills.update_faq(faq_id, "P nueva", "R nueva")

    assert skills.get_faqs()[0]["category"] == "Envíos"


def test_updating_an_unknown_id_reports_it_rather_than_writing(skills):
    skills.add_faq("P", "R")

    assert skills.update_faq("does-not-exist", "P", "R") is False
    assert len(skills.get_faqs()) == 1


def test_deleting_removes_only_the_one_block(skills):
    first = skills.add_faq("P1", "R1")
    second = skills.add_faq("P2", "R2")

    assert skills.delete_faq(first) is True

    remaining = skills.get_faqs()
    assert [f["id"] for f in remaining] == [second]
    assert remaining[0]["question"] == "P2"


def test_deleting_an_unknown_id_reports_it_rather_than_emptying_the_file(skills):
    skills.add_faq("P", "R")

    assert skills.delete_faq("does-not-exist") is False
    assert len(skills.get_faqs()) == 1


def test_the_store_survives_a_new_manager_over_the_same_directory(tmp_path):
    """The file is the store, not the instance. The API builds a manager per
    request, so a FAQ added on one has to be visible to the next."""
    faq_id = SkillManager(memory_dir=tmp_path).add_faq("P", "R")

    reopened = SkillManager(memory_dir=tmp_path).get_faqs()

    assert [f["id"] for f in reopened] == [faq_id]
