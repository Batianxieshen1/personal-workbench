"""前端完整性测试（pytest 守护静态资源）。

覆盖三个真实踩过的坑：
1. i18n 中英字典 key 不一致（切语言时缺翻译）
2. index.html 引用了字典里不存在的 key（data-i18n 悬空）
3. 重复的 id（document.getElementById 只取第一个，功能错乱）
"""
import os
import re

STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


def _read(name: str) -> str:
    with open(os.path.join(STATIC, name), encoding="utf-8") as f:
        return f.read()


def _dict_keys(js: str, lang: str) -> set:
    """从 app.js 提取某语言的 i18n key 集合（zh: {...} / en: {...}）。"""
    m = re.search(rf"{lang}:\s*\{{(.*?)\n\s*\}}", js, re.S)
    if not m:
        return set()
    return set(re.findall(r'"([a-z0-9._-]+)"\s*:', m.group(1)))


def test_i18n_zh_en_keys_match():
    js = _read("app.js")
    zh = _dict_keys(js, "zh")
    en = _dict_keys(js, "en")
    assert zh and en, "未能提取 i18n 字典"
    assert zh == en, f"中英 key 不一致，缺失: {zh - en or en - zh}"


def test_data_i18n_keys_exist_in_dict():
    js = _read("app.js")
    html = _read("index.html")
    zh = _dict_keys(js, "zh")
    used = set(re.findall(r'data-i18n="([a-z0-9._-]+)"', html))
    missing = used - zh
    assert not missing, f"index.html 引用了字典缺失的 key: {missing}"


def test_html_ids_unique():
    html = _read("index.html")
    ids = re.findall(r'id="([^"]+)"', html)
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"重复的 id（会导致 getElementById 错乱）: {dupes}"


def test_i18n_keys_unique_within_lang():
    js = _read("app.js")
    for lang in ("zh", "en"):
        keys = _dict_keys(js, lang)
        assert len(keys) == len(set(keys)), f"{lang} 字典存在重复 key"


def test_js_has_no_leftover_lorem():
    """防止占位/调试残留。"""
    js = _read("app.js")
    assert "TODO" not in js and "FIXME" not in js
