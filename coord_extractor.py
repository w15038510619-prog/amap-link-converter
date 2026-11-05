# -*- coding: utf-8 -*-
"""
地图链接目的地经纬度提取模块
核心原则:
1. 提取目的地 (终点)，严禁误取起点 (from/sn/slon/slat)、当前定位、途经点或地图视图中心 (@x,y,zoom)。
2. 支持多种高德链接:
   - __r=lat1,lon1,name1,lat2,lon2,name2... (路径或查询参数)
   - r=lat1,lon1,name1,lat2,lon2,name2... (高德网页路由)
   - daddr=lon,lat,name... (经度在前，交叉校验)
   - to[lnglat]=lon,lat
   - schema=amapuri://route/plan (提取 dlon, dlat，忽略 slon, slat，支持参数乱序)
   - 高德分享链接 urlParameter (调用 amap_api 接口)
3. 支持百度地图链接:
   - map.baidu.com/dir/... 中提取 en=
   - 支持 BD09MC (大数值墨卡托) -> BD-09 -> GCJ-02
   - 支持已为 BD-09 经纬度 -> GCJ-02
   - 严禁提取 sn= 起点和 @ 视图中心
4. 严格校验分层解码，防止逗号截断破坏结构。
"""

import math
import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Tuple

from coord_transform import (
    bd09_to_gcj02,
    bd09mc_to_gcj02,
    bd09mc_to_bd09,
    is_valid_lnglat,
)
from amap_api import fetch_amap_share_info


@dataclass
class ExtractionResult:
    lon: float
    lat: float
    coord_sys: str  # 统一转换为 GCJ-02
    method: str
    intermediate_info: str = ""


class CoordExtractionError(Exception):
    """解析经纬度异常基类"""
    pass


def _parse_amap_r_payload(payload: str) -> Optional[Tuple[float, float]]:
    """
    解析 __r 或 r 的参数段:
    payload 格式通常为: lat1,lon1,name1,lat2,lon2,name2,...
    返回: (lon, lat) 或 None
    注意:
    高德 r/ __r 参数中，每组坐标顺序为 (纬度, 经度)!
    第 1 组是起点 (lat1, lon1)
    第 2 组是终点 (lat2, lon2) -> 我们要提取的是第 2 组!
    """
    if not payload:
        return None
    # 逗号分割，注意此时不宜进行全量百分号解码，因为名称内若有编码的逗号会破坏分段
    parts = payload.split(",")
    if len(parts) >= 5:
        try:
            lat2 = float(parts[3])
            lon2 = float(parts[4])
            # 合法性校验
            if -90.0 <= lat2 <= 90.0 and -180.0 <= lon2 <= 180.0:
                return lon2, lat2
        except (ValueError, TypeError):
            pass
    return None


def _parse_daddr_payload(payload: str) -> Optional[Tuple[float, float]]:
    """
    解析 daddr 参数段:
    daddr 格式通常为: lon,lat,name 或 lon,lat
    注意: daddr 顺序是 (经度, 纬度)!
    返回: (lon, lat) 或 None
    """
    if not payload:
        return None
    parts = payload.split(",")
    if len(parts) >= 2:
        try:
            lon = float(parts[0])
            lat = float(parts[1])
            if -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0:
                return lon, lat
        except (ValueError, TypeError):
            pass
    return None


def _parse_amap_schema(schema_str: str) -> Optional[Tuple[float, float]]:
    """
    解析嵌套 schema 中的 amapuri://route/plan 终点
    支持参数乱序，提取 dlon, dlat，禁止取 slon, slat
    """
    if not schema_str:
        return None
    # 最多有限解码 2 次
    cur = schema_str
    for _ in range(2):
        if "%" in cur:
            cur = urllib.parse.unquote(cur)

    # 验证是否为 route/plan 协议
    if "amapuri://" in cur or "route/plan" in cur or "dlon=" in cur or "dlat=" in cur:
        m_dlon = re.search(r"(?:^|[?&])dlon=([0-9.-]+)", cur)
        m_dlat = re.search(r"(?:^|[?&])dlat=([0-9.-]+)", cur)
        if m_dlon and m_dlat:
            try:
                lon = float(m_dlon.group(1))
                lat = float(m_dlat.group(1))
                if -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0:
                    return lon, lat
            except ValueError:
                pass
    return None


def _parse_amap_to_lnglat(url: str) -> Optional[Tuple[float, float]]:
    """
    提取 to[lnglat] 参数:
    支持 to[lnglat]=118.08428674936296,24.4892099334146
    及 url 编码形式 to%5Blnglat%5D=118.08428674936296%2C24.4892099334146
    顺序为: (lng, lat)
    """
    # 匹配未编码或编码形式
    m = re.search(r"(?:to\[lnglat\]|to%5B(?:lnglat|LNGLAT)%5D)=([^&?#]+)", url, re.IGNORECASE)
    if m:
        raw_val = m.group(1)
        decoded_val = urllib.parse.unquote(raw_val)
        parts = decoded_val.split(",")
        if len(parts) >= 2:
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                if -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0:
                    return lon, lat
            except ValueError:
                pass
    return None


def _parse_baidu_dir_en(url: str) -> Optional[Tuple[float, float, str, str]]:
    """
    解析百度地图链接中的终点 en=
    格式可能为:
    1. en=1$$$$13145007,2792306$$终点$$0$$$$ (BD09MC 墨卡托)
    2. en=13145007,2792306
    3. en=name:终点|latlng:24.464899,118.082322 (BD-09 经纬度)
    禁止提取: sn= (起点), @x,y,z (视图中心)
    返回: (gcj_lon, gcj_lat, method, intermediate_info) 或 None
    """
    # 仅在百度地图链接或包含 en= 的结构中查找
    if "baidu.com" not in url and "en=" not in url:
        return None

    # 分层提取 en 参数值，不整体破坏
    m_en = re.search(r"(?:^|[?&])en=([^&]+)", url)
    if not m_en:
        return None

    raw_en = m_en.group(1)
    # 单次解码
    decoded_en = urllib.parse.unquote(raw_en)

    # 匹配数字对 (可能是墨卡托大数或经纬度)
    # 情况 A: 包含逗号分隔的两组数字
    # 例如 13145007,2792306 或 118.082322,24.464899 或 24.464899,118.082322
    coord_pairs = re.findall(r"([-+]?\d+(?:\.\d+)?)[,\s]+([-+]?\d+(?:\.\d+)?)", decoded_en)
    if not coord_pairs:
        return None

    # 取最后一组有效的数字对 (避免取到前面的类型标号如 1$$)
    v1_str, v2_str = coord_pairs[-1]
    try:
        val1 = float(v1_str)
        val2 = float(v2_str)
    except ValueError:
        return None

    # 判断是否为墨卡托米制坐标 (BD09MC)
    # 墨卡托坐标通常 X > 100000 且 Y > 100000
    if abs(val1) > 1000.0 or abs(val2) > 1000.0:
        mc_x, mc_y = val1, val2
        bd_lon, bd_lat = bd09mc_to_bd09(mc_x, mc_y)
        gcj_lon, gcj_lat = bd09_to_gcj02(bd_lon, bd_lat)
        intermediate = f"BD09MC({mc_x}, {mc_y}) -> BD-09({bd_lon:.6f}, {bd_lat:.6f})"
        return gcj_lon, gcj_lat, "baidu_en_bd09mc", intermediate

    # 否则已是经纬度，判断经纬度顺序:
    # 经度通常在 70~140 (中国范围内)，纬度在 15~55
    # 如果 val1 在 70~140，则 val1 为 lon, val2 为 lat
    # 如果 val1 在 15~55 且 val2 在 70~140，则说明是 lat, lon 顺序
    if (70.0 <= val1 <= 140.0) and (-90.0 <= val2 <= 90.0):
        bd_lon, bd_lat = val1, val2
    elif (70.0 <= val2 <= 140.0) and (-90.0 <= val1 <= 90.0):
        bd_lon, bd_lat = val2, val1
    else:
        # 无法判断顺序，保守处理
        bd_lon, bd_lat = val1, val2

    gcj_lon, gcj_lat = bd09_to_gcj02(bd_lon, bd_lat)
    intermediate = f"BD-09({bd_lon:.6f}, {bd_lat:.6f})"
    return gcj_lon, gcj_lat, "baidu_en_bd09ll", intermediate


def extract_destination(
    url_or_text: str,
    allow_network: bool = True
) -> ExtractionResult:
    """
    从位置链接或文本中提取目的地 GCJ-02 经纬度
    url_or_text: 输入的 URL 或文本
    allow_network: 是否允许在无法离线解析时请求高德分享接口
    """
    if not url_or_text or not isinstance(url_or_text, str):
        raise CoordExtractionError("位置内容为空")

    raw_text = url_or_text.strip()
    if not raw_text:
        raise CoordExtractionError("位置内容为空白字符")

    # 1. 优先检查高德 __r 路由参数 (可能在路径中或查询参数中)
    m_double_r = re.search(r"__r=([^&?#]+)", raw_text)
    # 2. 检查高德 r 路由参数
    m_single_r = re.search(r"(?:^|[?&/])r=([^&?#]+)", raw_text)
    # 3. 检查 daddr 参数 (可能在路径中或查询参数中)
    m_daddr = re.search(r"(?:^|[?&/])daddr=([^&?#]+)", raw_text)

    coords_r = None
    if m_double_r:
        coords_r = _parse_amap_r_payload(m_double_r.group(1))
    elif m_single_r:
        coords_r = _parse_amap_r_payload(m_single_r.group(1))

    coords_daddr = None
    if m_daddr:
        coords_daddr = _parse_daddr_payload(m_daddr.group(1))

    # 若同时存在 __r/r 与 daddr，交叉核验终点
    if coords_r and coords_daddr:
        diff_lon = abs(coords_r[0] - coords_daddr[0])
        diff_lat = abs(coords_r[1] - coords_daddr[1])
        if diff_lon > 0.0001 or diff_lat > 0.0001:
            raise CoordExtractionError(
                f"目的地坐标冲突: 路由终点({coords_r[0]:.6f}, {coords_r[1]:.6f}) 与 "
                f"daddr({coords_daddr[0]:.6f}, {coords_daddr[1]:.6f}) 差异超过阈值"
            )
        # 一致，采用精度更完整的高德 r 终点
        return ExtractionResult(
            lon=coords_r[0],
            lat=coords_r[1],
            coord_sys="GCJ-02",
            method="amap_r_and_daddr_verified"
        )
    elif coords_r:
        return ExtractionResult(
            lon=coords_r[0],
            lat=coords_r[1],
            coord_sys="GCJ-02",
            method="amap_r"
        )
    elif coords_daddr:
        return ExtractionResult(
            lon=coords_daddr[0],
            lat=coords_daddr[1],
            coord_sys="GCJ-02",
            method="amap_daddr"
        )

    # 4. 检查 to[lnglat] 参数
    coords_to = _parse_amap_to_lnglat(raw_text)
    if coords_to:
        return ExtractionResult(
            lon=coords_to[0],
            lat=coords_to[1],
            coord_sys="GCJ-02",
            method="amap_to_lnglat"
        )

    # 5. 检查 schema 嵌套 amapuri://route/plan
    m_schema = re.search(r"(?:schema|backSchema)=([^&?#]+)", raw_text, re.IGNORECASE)
    if m_schema:
        coords_schema = _parse_amap_schema(m_schema.group(1))
        if coords_schema:
            return ExtractionResult(
                lon=coords_schema[0],
                lat=coords_schema[1],
                coord_sys="GCJ-02",
                method="amap_schema_plan"
            )

    # 6. 检查百度地图 en= 终点
    baidu_res = _parse_baidu_dir_en(raw_text)
    if baidu_res:
        lon, lat, method, intermediate = baidu_res
        valid, msg = is_valid_lnglat(lon, lat)
        if not valid:
            raise CoordExtractionError(f"百度坐标解析结果异常: {msg}")
        return ExtractionResult(
            lon=lon,
            lat=lat,
            coord_sys="GCJ-02",
            method=method,
            intermediate_info=intermediate
        )

    # 7. 检查是否为高德分享页面 (含 urlParameter 或 shareParam)
    m_token = re.search(r"(?:urlParameter|shareParam|param)=([^&?#]+)", raw_text)
    is_amap_domain = any(d in raw_text for d in ["amap.com", "autonavi.com"])
    if m_token and is_amap_domain:
        if not allow_network:
            raise CoordExtractionError("该链接为高德动态分享链接，离线模式下无法请求解析")
        token_val = m_token.group(1)
        try:
            api_lon, api_lat, api_method = fetch_amap_share_info(token_val)
            valid, msg = is_valid_lnglat(api_lon, api_lat)
            if not valid:
                raise CoordExtractionError(f"高德分享接口返回坐标非法: {msg}")
            return ExtractionResult(
                lon=api_lon,
                lat=api_lat,
                coord_sys="GCJ-02",
                method=api_method,
                intermediate_info="动态接口实时解析"
            )
        except Exception as e:
            raise CoordExtractionError(f"高德分享接口恢复终点失败: {e}")

    # 8. 文本中已明确标注经纬度与坐标系的情况检查
    # 例如：GCJ-02: 118.238, 24.658
    m_explicit_gcj = re.search(r"(?:GCJ-?02|火星坐标系)[\s:：]+([0-9.-]+)[\s,，]+([0-9.-]+)", raw_text, re.IGNORECASE)
    if m_explicit_gcj:
        try:
            v1 = float(m_explicit_gcj.group(1))
            v2 = float(m_explicit_gcj.group(2))
            # 经度在前或在后
            lon, lat = (v1, v2) if abs(v1) > abs(v2) else (v2, v1)
            valid, msg = is_valid_lnglat(lon, lat)
            if valid:
                return ExtractionResult(
                    lon=lon,
                    lat=lat,
                    coord_sys="GCJ-02",
                    method="explicit_gcj02_text"
                )
        except ValueError:
            pass

    # 若发现纯数字经纬度但未标明坐标系：严禁猜测坐标系，报错提醒
    m_bare_nums = re.search(r"^\s*([0-9]{2,3}(?:\.[0-9]+)?)[,\s]+([0-9]{2,3}(?:\.[0-9]+)?)\s*$", raw_text)
    if m_bare_nums:
        raise CoordExtractionError("文本包含数值但未明确标注坐标系(GCJ-02/BD-09/WGS84)，禁止猜测坐标系")

    # 未能识别的链接类型
    raise CoordExtractionError("不支持的地图链接或未在内容中找到有效终点信息")
