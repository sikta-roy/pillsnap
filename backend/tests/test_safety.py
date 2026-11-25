from app import safety
from app.config import CONFIDENCE_THRESHOLD


def test_dose_sentences_are_removed():
    text = "It relieves pain. Take 2 tablets every 6 hours. Do not exceed 4000 mg per day. Avoid alcohol."
    out = safety.strip_doses(text)
    assert "tablets every" not in out and "4000" not in out
    assert "relieves pain" in out and "Avoid alcohol" in out


def test_strength_in_names_is_not_a_dose():
    assert not safety.contains_dose("Dolo 650 contains paracetamol.")
    assert safety.contains_dose("Take one tablet twice a day.")


def test_dose_questions_detected():
    for q in ["How much should I take?", "what is the dose", "कितनी गोली लूँ", "can I take it 3 times a day"]:
        assert safety.is_dose_question(q), q
    assert not safety.is_dose_question("Can it make me sleepy?")


def test_low_confidence_never_gives_single_answer():
    m = [{"confidence": 0.65}, {"confidence": 0.2}]
    status, _ = safety.decide(m, imprint_read=True, imprint_match=1.0)
    assert status == "needs_confirmation"


def test_no_imprint_caps_confidence():
    m = [{"confidence": 0.95}]
    status, out = safety.decide(m, imprint_read=False, imprint_match=None)
    assert status == "needs_confirmation"
    assert out[0]["confidence"] < CONFIDENCE_THRESHOLD


def test_confident_needs_imprint_and_threshold():
    status, _ = safety.decide([{"confidence": 0.9}], imprint_read=True, imprint_match=0.95)
    assert status == "confident"


def test_disclaimer_in_both_languages():
    assert "pharmacist" in safety.DISCLAIMER["en"]
    assert "फार्मासिस्ट" in safety.DISCLAIMER["hi"]
