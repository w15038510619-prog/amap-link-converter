# -*- coding: utf-8 -*-
"""
高德分享接口单元测试
包含模拟接口响应测试 (成功、过期、超时、缺字段) 及真实样例测试
"""

from unittest.mock import patch, MagicMock
import pytest
from amap_api import fetch_amap_share_info, mask_token


def test_mask_token():
    assert mask_token("") == ""
    assert mask_token("short") == "***"
    token = "abcdefghijklmnopqrstuvwxyz"
    masked = mask_token(token)
    assert masked.startswith("abcd...")
    assert masked.endswith("wxyz (长度: 26)")
    assert "efgh" not in masked


def test_amap_api_success_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"code":"1","data":{"endPointLon":"118.238461","endPointLat":"24.658314"}}'

    with patch("requests.get", return_value=mock_resp):
        lon, lat, method = fetch_amap_share_info("mock_token_12345678")
        assert abs(lon - 118.238461) < 1e-6
        assert abs(lat - 24.658314) < 1e-6
        assert method == "amap_share_api"


def test_amap_api_backschema_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = (
        '{"code":"1","data":{"backSchema":"amapuri://route/plan?slat=24.1&slon=118.1&dlat=24.658314&dlon=118.238461"}}'
    )

    with patch("requests.get", return_value=mock_resp):
        lon, lat, method = fetch_amap_share_info("mock_token_12345678")
        assert abs(lon - 118.238461) < 1e-6
        assert abs(lat - 24.658314) < 1e-6
        assert method == "amap_share_api_backschema"


def test_amap_api_expired_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"code":"0","message":"分享信息已失效或不存在"}'

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ValueError, match="分享信息已失效"):
            fetch_amap_share_info("expired_token_123456")


def test_amap_api_missing_fields_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"code":"1","data":{"status":1}}'

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ValueError, match="未包含有效终点坐标"):
            fetch_amap_share_info("token_no_coords_123456")


def test_amap_api_live_sample():
    """使用源表中的真实 shareParam 运行一次真实请求验证"""
    real_param = (
        "Ig3Pq%2BHPYz73CQevu6X2yZm2teSLmUGDRiqn0fduTiJ1PJaaNM%2BBdpZY5n9dNTNCuMT%2FsldO2FohdvDh2a9LE5"
        "%2BEqKGsNUKqvgyj8szjafmPGnyWL7GBBrNJupwEtHgg"
    )
    try:
        lon, lat, _ = fetch_amap_share_info(real_param, timeout=4, max_retries=1)
        assert abs(lon - 118.238461) < 1e-5
        assert abs(lat - 24.658314) < 1e-5
    except (TimeoutError, ConnectionError):
        pytest.skip("当前网络环境不可达高德服务器，跳过 live 测试")
