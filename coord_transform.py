# -*- coding: utf-8 -*-
"""
坐标转换与校验模块
支持:
1. 百度墨卡托平面坐标 (BD09MC) -> 百度经纬度坐标 (BD-09)
2. 百度经纬度坐标 (BD-09) -> 火星坐标系 (GCJ-02)
3. 坐标范围合法性校验及异常检测
"""

import math
from typing import Tuple

# 百度墨卡托分带与多项式转换参数 (逆投影)
MCBAND = (12890594.86, 8362377.87, 5591021.0, 3481989.83, 1678043.12, 0.0)
MC2LL = (
    (1.410526172116255e-8, 0.00000898305509648872, -1.9939833816331, 200.9824383106796, -187.2403703815547,
     91.6087516669843, -23.38765649603339, 2.57121317296198, -0.03801003308653, 17337981.2),
    (-7.435856389565537e-9, 0.000008983055097726239, -0.78625201886289, 96.32687599759846, -1.85204757529826,
     -59.36935905485877, 47.40033549296737, -16.50741931063887, 2.28786674699375, 10260144.86),
    (-3.030883460898826e-8, 0.00000898305509983578, 0.30071316287616, 59.74293618442277, 7.357984074871,
     -25.38371002664745, 13.45380521110908, -3.29883767235584, 0.32710905363475, 6856817.37),
    (-1.981981304930552e-8, 0.000008983055099779535, 0.03278182852591, 40.31678527705744, 0.65659298677277,
     -4.44255534477492, 0.85341911805263, 0.12923347998204, -0.04625736007561, 4482777.06),
    (3.09191371068437e-9, 0.000008983055096812155, 0.00006995724062, 23.10934304144901, -0.00023663490511,
     -0.6321817810242, -0.00663494467273, 0.03430082397953, -0.00466043876332, 2555164.4),
    (2.890871144776878e-9, 0.000008983055095805407, -3.068298e-8, 7.47137025468032, -0.00000353937994,
     -0.02145144861037, -0.00001234426596, 0.00010322952773, -0.00000323890364, 826088.5)
)

X_PI = 3.14159265358979324 * 3000.0 / 180.0


def bd09mc_to_bd09(mc_x: float, mc_y: float) -> Tuple[float, float]:
    """
    百度墨卡托平面坐标 (BD09MC) 转 百度经纬度 (BD-09)
    mc_x: 墨卡托 X (米)
    mc_y: 墨卡托 Y (米)
    返回: (bd_lon, bd_lat)
    """
    lat_abs = abs(mc_y)
    selected_coeff = MC2LL[-1]
    for i in range(len(MCBAND)):
        if lat_abs >= MCBAND[i]:
            selected_coeff = MC2LL[i]
            break

    c_e = selected_coeff
    t = c_e[0] + c_e[1] * abs(mc_x)
    c_c = abs(mc_y) / c_e[9]
    c_f = (
        c_e[2]
        + c_e[3] * c_c
        + c_e[4] * (c_c ** 2)
        + c_e[5] * (c_c ** 3)
        + c_e[6] * (c_c ** 4)
        + c_e[7] * (c_c ** 5)
        + c_e[8] * (c_c ** 6)
    )

    t = t * (-1 if mc_x < 0 else 1)
    c_f = c_f * (-1 if mc_y < 0 else 1)
    return t, c_f


def bd09_to_gcj02(bd_lon: float, bd_lat: float) -> Tuple[float, float]:
    """
    百度经纬度 (BD-09) 转 火星坐标系 (GCJ-02)
    bd_lon: 百度经度
    bd_lat: 百度纬度
    返回: (gcj_lon, gcj_lat)
    """
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * X_PI)
    gcj_lon = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)
    return gcj_lon, gcj_lat


def bd09mc_to_gcj02(mc_x: float, mc_y: float) -> Tuple[float, float]:
    """
    百度墨卡托平面坐标 (BD09MC) -> BD-09 -> GCJ-02
    """
    bd_lon, bd_lat = bd09mc_to_bd09(mc_x, mc_y)
    return bd09_to_gcj02(bd_lon, bd_lat)


def is_valid_lnglat(lon: float, lat: float) -> Tuple[bool, str]:
    """
    检查经纬度是否在合法有限数值范围内
    经度: [-180, 180]
    纬度: [-90, 90]
    """
    if not (isinstance(lon, (int, float)) and isinstance(lat, (int, float))):
        return False, f"经纬度必须为数值类型，实际为: lon={type(lon)}, lat={type(lat)}"
    if math.isnan(lon) or math.isnan(lat) or math.isinf(lon) or math.isinf(lat):
        return False, f"经纬度包含 NaN 或 Inf: lon={lon}, lat={lat}"
    if not (-180.0 <= lon <= 180.0):
        return False, f"经度超出合法范围 [-180, 180]: {lon}"
    if not (-90.0 <= lat <= 90.0):
        return False, f"纬度超出合法范围 [-90, 90]: {lat}"
    return True, ""


def is_xiamen_region(lon: float, lat: float) -> bool:
    """
    参考性判断：主要点位是否在厦门及周边区域 (福建沿海 ~ 经度 117.5-118.8, 纬度 24.1-25.2)
    仅用于离群记录日志提示，不截断或丢弃任何其他合法坐标。
    """
    return (117.0 <= lon <= 119.5) and (23.5 <= lat <= 26.0)
