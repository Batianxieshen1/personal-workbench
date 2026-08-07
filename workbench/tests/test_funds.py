"""基金模块测试：净值解析、涨跌计算、历史曲线、缓存。"""
import json

from app import funds, storage

PINGZHONG_SAMPLE = """
var fS_name = "天弘沪深300";
var fund_info = {"code": "000961"};
var Data_netWorthTrend = [
  {"x": 1750000000000, "y": 1.2000, "equityReturn": 0.5},
  {"x": 1750086400000, "y": 1.2200, "equityReturn": 1.67},
  {"x": 1750172800000, "y": 1.2100, "equityReturn": -0.82}
];
"""


class _FakeResp:
    def __init__(self, text):
        self.text = text
        self.status_code = 200

    def raise_for_status(self):
        pass


def test_parse_fund_data():
    d = funds.parse_pingzhong(PINGZHONG_SAMPLE)
    assert d["name"] == "天弘沪深300"
    assert d["code"] == "000961"
    assert d["latest"] == 1.21
    # 最近一个净值日的涨跌（-0.82%）
    assert abs(d["change_pct"] - (-0.82)) < 0.001
    assert len(d["history"]) == 3


def test_get_funds_list(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("funds.json", {"funds": [{"code": "000961"}]})
    monkeypatch.setattr(funds.requests, "get",
                        lambda url, timeout=10, headers=None: _FakeResp(PINGZHONG_SAMPLE))
    result = funds.get_funds()
    assert result["funds"][0]["name"] == "天弘沪深300"
    assert "change_pct" in result["funds"][0]
    assert result["funds"][0]["latest"] == 1.21


def test_add_remove_fund(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("funds.json", {"funds": []})
    monkeypatch.setattr(funds.requests, "get",
                        lambda url, timeout=10, headers=None: _FakeResp(PINGZHONG_SAMPLE))
    funds.add_fund("000961")
    assert funds.list_codes() == ["000961"]
    funds.remove_fund("000961")
    assert funds.list_codes() == []


def test_duplicate_fund_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save("funds.json", {"funds": []})  # 清空默认列表
    funds.add_fund("000961")
    funds.add_fund("000961")  # 重复添加被忽略
    assert funds.list_codes() == ["000961"]


def test_get_history(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(funds.requests, "get",
                        lambda url, timeout=10, headers=None: _FakeResp(PINGZHONG_SAMPLE))
    hist = funds.get_history("000961")
    assert len(hist["points"]) == 3
    assert "date" in hist["points"][0]
    assert "value" in hist["points"][0]
