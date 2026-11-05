# -*- coding: utf-8 -*-
"""
链接经纬度提取全场景测试
包含:
1. 高德 __r= (含路径中无问号结构)
2. 高德 r= (网页路由)
3. 高德 daddr=
4. 高德 __r 与 daddr 交叉核对 (一致 vs 冲突)
5. 高德 to[lnglat] 与 from[lnglat] (禁止误取起点)
6. 嵌套 schema amapuri://route/plan (乱序参数、忽略 slon/slat)
7. 百度地图 en= (BD09MC 与 BD-09经纬度，忽略 sn= 和 @x,y,zoom)
8. 空白、未知网站及非法数值异常
"""

import pytest
from coord_extractor import extract_destination, CoordExtractionError


def test_amap_double_r_in_path():
    """测试提示词中的高德 __r 样例"""
    url = "https://m.amap.com/navigation/carmap/__r=24.525608,118.145143,起点,24.658314840498143,118.23846146464349,终点,,0,0"
    res = extract_destination(url)
    assert abs(res.lon - 118.23846146464349) < 1e-7
    assert abs(res.lat - 24.658314840498143) < 1e-7
    assert res.coord_sys == "GCJ-02"


def test_amap_web_route_r():
    """测试提示词中的高德网页路由 r= 样例 (无协议头)"""
    url = "amap.com/?r=24.47943,118.10924,南湖中祥大厦,24.507583804788233,118.10855001211168,地图选定位置,,0,0"
    res = extract_destination(url)
    assert abs(res.lon - 118.10855001211168) < 1e-7
    assert abs(res.lat - 24.507583804788233) < 1e-7


def test_amap_daddr_alone():
    """测试单独的 daddr 参数"""
    url = "https://ditu.amap.com/dir?saddr=118.1,24.1,起点&daddr=118.23846146464349,24.658314840498143,终点"
    res = extract_destination(url)
    assert abs(res.lon - 118.23846146464349) < 1e-7
    assert abs(res.lat - 24.658314840498143) < 1e-7


def test_amap_r_and_daddr_crosscheck():
    """测试 __r 与 daddr 一致时通过，冲突时报错"""
    # 一致
    url_ok = (
        "https://m.amap.com/navigation/carmap/__r=24.525608,118.145143,起点,24.658314,118.238461,终点,,0,0"
        "&daddr=118.238461,24.658314,终点"
    )
    res = extract_destination(url_ok)
    assert abs(res.lon - 118.238461) < 1e-5
    assert abs(res.lat - 24.658314) < 1e-5

    # 明显冲突
    url_conflict = (
        "https://m.amap.com/navigation/carmap/__r=24.525608,118.145143,起点,24.658314,118.238461,终点,,0,0"
        "&daddr=119.500000,25.500000,终点"
    )
    with pytest.raises(CoordExtractionError, match="冲突"):
        extract_destination(url_conflict)


def test_amap_to_lnglat_order_and_ignore_from():
    """测试 to[lnglat] 提取，确保不误取 from[lnglat]"""
    url = (
        "https://www.amap.com/dir?from%5Blnglat%5D=118.10917%2C24.479792"
        "&to%5Blnglat%5D=118.08428674936296%2C24.4892099334146&policy=1&type=car"
    )
    res = extract_destination(url)
    assert abs(res.lon - 118.08428674936296) < 1e-7
    assert abs(res.lat - 24.4892099334146) < 1e-7


def test_amap_nested_schema_param_order():
    """测试嵌套 schema，参数乱序 (dlon在dlat后 或 dlat在dlon后)，忽略 slon/slat"""
    # dlon 在后
    url1 = (
        "https://act.amap.com/activity/2020CommonLanding/index.html?param=1"
        "&schema=amapuri%3A%2F%2Froute%2Fplan%3Fslat%3D24.111%26dlat%3D24.5678%26slon%3D118.111%26dlon%3D118.8765"
    )
    res1 = extract_destination(url1)
    assert abs(res1.lon - 118.8765) < 1e-5
    assert abs(res1.lat - 24.5678) < 1e-5

    # dlon 在前
    url2 = (
        "https://act.amap.com/activity/2020CommonLanding/index.html"
        "?schema=amapuri%3A%2F%2Froute%2Fplan%3Fdlon%3D118.8765%26other%3D123%26dlat%3D24.5678"
    )
    res2 = extract_destination(url2)
    assert abs(res2.lon - 118.8765) < 1e-5
    assert abs(res2.lat - 24.5678) < 1e-5


def test_baidu_en_bd09mc():
    """测试百度地图 en= 中的 BD09MC 墨卡托大数转为 GCJ-02，并忽略 sn 和 @ 视图中心"""
    url = (
        "https://map.baidu.com/dir/?qt=nav"
        "&sn=1$$$$13140000,2790000$$起点$$0$$$$"
        "&en=1$$$$13145007,2792306$$终点$$0$$$$"
        "&sc=224@13142000,2791000,14z"
    )
    res = extract_destination(url)
    # 期望 BD09MC (13145007, 2792306) -> BD-09 (118.082322, 24.464900) -> GCJ-02
    assert abs(res.lon - 118.075911) < 1e-4
    assert abs(res.lat - 24.458558) < 1e-4
    assert res.method == "baidu_en_bd09mc"


def test_unsupported_or_empty_links():
    """测试非法、空、不支持的网站链接"""
    with pytest.raises(CoordExtractionError):
        extract_destination("")
    with pytest.raises(CoordExtractionError):
        extract_destination("   ")
    with pytest.raises(CoordExtractionError, match="不支持"):
        extract_destination("https://www.google.com/maps/place/something")
    with pytest.raises(CoordExtractionError, match="禁止猜测坐标系"):
        extract_destination("118.238, 24.658")
