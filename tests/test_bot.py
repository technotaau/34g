import json
from types import SimpleNamespace

from gaon34 import bot


class FakeMessages:
    def __init__(self, text, stop_reason="end_turn"):
        self.text, self.stop_reason, self.calls = text, stop_reason, []

    def create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=self.text)])


def fake_client(text, stop_reason="end_turn"):
    msgs = FakeMessages(text, stop_reason)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


def test_pack_routes_questions_by_village_name_in_both_scripts():
    pack = bot.build_pack()
    assert bot.find_villages("कुम्भाणा में 1981 में कितने लोग थे?", pack) == ["kumbhana"]
    assert bot.find_villages("Kumbhana ke bare me batao", pack) == ["kumbhana"]
    assert set(bot.find_villages("kanolai aur thoiya", pack)) == {"kanolai", "thoiya"}
    assert bot.find_villages("33 गांव या 34?", pack) == []
    # every unit's facts plus the fixed part stay well inside one request
    assert len(bot.system_text(pack).encode()) < 20000
    assert max(len(v["text"].encode()) for v in pack["villages"].values()) < 16000


def test_answer_is_grounded_cached_and_uses_fallbacks():
    pack = bot.build_pack()
    client, msgs = fake_client("कुम्भाणा में 1,245 लोग रहते थे (जनगणना 1981)।")
    res = bot.answer("कुम्भाणा में कितने लोग थे?", pack=pack, client=client)
    kw = msgs.calls[0]
    assert kw["model"] == bot.DEFAULT_MODEL and kw["fallbacks"] == "default" and kw["betas"] == [bot.FALLBACK_BETA]
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "1,245" in kw["messages"][0]["content"]  # the village's census facts reach the prompt
    assert res["villages"] == ["kumbhana"] and "1,245" in res["text"]


def test_answer_handles_refusal_without_reading_content():
    client, _ = fake_client("", stop_reason="refusal")
    res = bot.answer("कुछ भी", pack=bot.build_pack(), client=client)
    assert res["stop_reason"] == "refusal" and res["text"] == bot.REFUSAL_HI


def test_extract_memory_uses_a_strict_schema():
    pack = bot.build_pack()
    out = {"village_slug": "thoiya", "village_as_said": "ठोइया", "language": "bagri", "summary_hi": "स्कूल की याद।",
           "topics": ["school"], "places": [], "years": ["1984"], "people_named": False, "sensitive": ["none"],
           "followup_questions": ["मास्टरजी कौन थे?"], "bagri_terms": [{"term": "पोसाळ", "meaning_hi": "पाठशाला"}]}
    client, msgs = fake_client(json.dumps(out, ensure_ascii=False))
    got = bot.extract_memory("म्हारी पोसाळ ठोइया में ही", "thoiya", pack=pack, client=client)
    schema = msgs.calls[0]["output_config"]["format"]["schema"]
    assert schema["additionalProperties"] is False and "thoiya" in schema["properties"]["village_slug"]["enum"]
    assert got["village_slug"] == "thoiya"


def test_pilot_page_embeds_the_pack_safely(tmp_path):
    path = bot.build_page(bot.build_pack(), tmp_path / "baat.html")
    html = path.read_text(encoding="utf-8")
    assert html.startswith("<title>") and "/*__PACK__*/null" not in html
    head, _, rest = html.partition("var PACK = ")
    data = rest.split(";\n  var SLUGS", 1)[0]
    assert "</script" not in data.lower()
    assert "kumbhana" in json.loads(data.replace("<\\/", "</"))["villages"]
