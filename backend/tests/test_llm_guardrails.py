from app.drugs.llm import Explanation, Statement, _validate
from app.drugs.rag import Chunk


def test_unsupported_or_uncited_statements_are_dropped():
    chunks = {
        "x:uses:0": Chunk("x:uses:0", "x", "uses", "Drug X. Uses: Relieves headache and fever", "label"),
        "x:storage:0": Chunk("x:storage:0", "x", "storage", "Drug X. Storage: Store below 30°C in a dry place.", "label"),
    }
    expl = Explanation(
        uses=[
            Statement(text="It relieves headache and fever.", source_ids=["x:uses:0"]),
            Statement(text="It also cures diabetes and cancer.", source_ids=["x:uses:0"]),  # not supported
            Statement(text="It relieves headache.", source_ids=["made:up:id"]),  # bad citation
            Statement(text="Take 2 tablets every 6 hours for headache.", source_ids=["x:uses:0"]),  # dose
        ],
        how_it_works=[], common_side_effects=[], serious_side_effects=[], who_should_not_take=[], warnings=[],
        storage=[Statement(text="Store it below 30°C in a dry place.", source_ids=["x:storage:0"])],
    )
    out, dropped = _validate(expl, chunks)
    assert [s["text"] for s in out["uses"]] == ["It relieves headache and fever."]
    assert len(out["storage"]) == 1
    assert dropped == 3
