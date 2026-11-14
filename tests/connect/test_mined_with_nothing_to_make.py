"""Mattias's report (3.0.10): The Apothecary Diaries S01 Ep 3, 4 and 8 read *No cards in Anki* — "It was mined, but
none of its cards are in Anki now: cards you deleted aren't made again unless you ask". He had deleted nothing: their
jobs ended `done` with `no words to make cards from`, every word they hold already on a card (患う made from Ep 2 a
moment before). The row couldn't tell "made, then deleted" from "nothing to make": its receipt with no card was both.

Now Connect's record names each item whose newest job found nothing to make (`status`'s `nothing`), the feed gives it
a NOTHING stone, and its row reads *Nothing new to mine* — its tip says why. A part whose cards were deleted still reads
*No cards in Anki*; one with cards still reads ✓.

What a wrong answer would cost: a learner told he deleted cards he never had, looking for them in Anki; or a part whose
cards he did delete said to have had nothing to make.

Against `FakeSteps` and a real ledger read by the real status record and feed; real Japanese words. No live Anki.
"""
from types import SimpleNamespace

from app.connect import feed, runner, status
from app.connect.ledger import Ledger, _now
from app.services import view_rows
from tests.connect.fake_steps import FakeSteps

WORDS = [("患う", "わずらう"), ("推測", "すいそく"), ("帰還", "きかん")]
DELETED = view_rows.Status("deleted", view_rows.STRINGS["deleted"], view_rows.STRINGS["tip_deleted"], "faint")


def _two_episodes(tmp_path):
    """Ep 1 and Ep 2 hold the same words: Ep 1 makes their cards, Ep 2 finds every one carded."""
    plan = {"line": {"ja": [1, 2]}, "queue": {"ja": [1, 2]}, "words": {"1": WORDS, "2": WORDS}}
    steps = FakeSteps(str(tmp_path), plan)
    path = str(tmp_path / "ledger.sqlite")
    with Ledger(path) as ledger:
        runner.run({}, ["ja"], steps=steps, ledger=ledger, sleep=lambda s: None, looks=1)
        got = {j["item_id"]: (j["state"], j.get("reason")) for j in ledger.jobs("ja")}
    assert got == {1: ("done", None), 2: ("done", runner.NO_WORDS)}, got
    return path


def _record(path):
    return status.read(languages=["ja"], path=path)


def test_an_episode_with_nothing_to_make_is_named_in_connects_record_and_one_that_made_cards_is_not(tmp_path):
    rec = _record(_two_episodes(tmp_path))["languages"]["ja"]
    assert rec["nothing"] == [2]


def test_its_row_reads_nothing_new_to_mine_never_cards_you_deleted(tmp_path):
    item = feed.build(_record(_two_episodes(tmp_path)), "ja").items[2]
    assert item.kind == feed.NOTHING and item.words == feed.WORDS[feed.NOTHING]
    st = view_rows._connected(DELETED, item, "video")
    assert (st.kind, st.label, st.tip, st.tone) == ("nothing", "Nothing new to mine", view_rows.STRINGS["tip_nothing"],
                                                    "faint")
    assert "deleted" not in st.tip


def test_a_nothing_stone_never_changes_an_episode_with_cards_or_one_not_mined():
    item = feed.Item(kind=feed.NOTHING, words="", tip="", job=None, made=0, total=0)
    in_anki = view_rows.Status("in_anki", "2", "", "ok")
    mine = view_rows.Status("mine", "Mine", "", "dim")
    assert view_rows._connected(in_anki, item, "video") is in_anki
    assert view_rows._connected(mine, item, "video") is mine


def test_a_shows_row_of_parts_with_nothing_to_make_says_so_and_a_deleted_part_keeps_its_words(tmp_path):
    connect = feed.build(_record(_two_episodes(tmp_path)), "ja").items
    eps = [SimpleNamespace(id=2, cards=0, deleted=True, online=None)]
    st = view_rows._row_connected(DELETED, eps, connect, "video")
    assert (st.kind, st.label) == ("nothing", "Nothing new to mine")
    deleted_too = eps + [SimpleNamespace(id=9, cards=0, deleted=True, online=None)]    # its cards deleted: no stone
    assert view_rows._row_connected(DELETED, deleted_too, connect, "video").kind == "deleted"


def test_a_new_try_under_way_is_no_longer_nothing_to_make(tmp_path):
    """*Mine* asked again (its cards deleted since, or new words listed): its own stone, never the old *Nothing*."""
    path = _two_episodes(tmp_path)
    with Ledger(path) as ledger, ledger.transaction():
        assert ledger.ask("ja", 2, _now(), store_id="store-1")[0] == "queued"
    assert _record(path)["languages"]["ja"]["nothing"] == []
    assert feed.build(_record(path), "ja").items[2].kind == feed.ASKED


def test_an_empty_ledger_names_nothing(tmp_path):
    with Ledger(str(tmp_path / "ledger.sqlite")):
        pass
    assert _record(str(tmp_path / "ledger.sqlite"))["languages"]["ja"]["nothing"] == []
