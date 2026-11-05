# -*- coding: utf-8 -*-
"""
坐标转换与回归测试
"""

import math
import pytest
from coord_transform import (
    bd09mc_to_bd09,
    bd09_to_gcj02,
    bd09mc_to_gcj02,
    is_valid_lnglat,
    is_xiamen_region,
)


def test_bd09mc_regression_example():
    """
    提示词中明确给出的中间值回归样例:
    BD09MC (13145007, 2792306) 转出的 BD-09 经度约 118.082322132073、纬度约 24.464899785808。
    """
    mc_x = 13145007.0
    mc_y = 2792306.0
    bd_lon, bd_lat = bd09mc_to_bd09(mc_x, mc_y)

    assert abs(bd_lon - 118.082322132073) < 1e-6
    assert abs(bd_lat - 24.464899785808) < 1e-6


def test_bd09_to_gcj02_conversion():
    """测试 BD-09 转 GCJ-02 转换"""
    bd_lon = 118.082322132073
    bd_lat = 24.464899785808
    gcj_lon, gcj_lat = bd09_to_gcj02(bd_lon, bd_lat)

    # 结果应在厦门附近
    assert 118.0 < gcj_lon < 118.2
    assert 24.4 < gcj_lat < 24.6
    assert is_xiamen_region(gcj_lon, gcj_lat)


def test_is_valid_lnglat():
    """测试经纬度边界与异常判断"""
    # 正常
    ok, _ = is_valid_lnglat(118.1, 24.5)
    assert ok

    # 边界
    assert is_valid_lnglat(180.0, 90.0)[0]
    assert is_valid_lnglat(-180.0, -90.0)[0]

    # 超出范围
    assert not is_valid_lnglat(180.1, 24.0)[0]
    assert not is_valid_lnglat(118.0, 90.5)[0]

    # 非法浮点
    assert not is_valid_lnglat(float("nan"), 24.0)[0]
    assert not is_valid_lnglat(118.0, float("inf"))[0]
