# -*- coding: utf-8 -*-
"""
高德分享页接口模块
处理形如 https://static3.amap.com/activity/2020NewDriveSafeV5/index.html?...&urlParameter=... 的分享链接。
通过调用高德公开接口 GET https://m5.amap.com/ws/user/route/share/info?param=<urlParameter> 获取终点。
"""

import json
import logging
import re
import urllib.parse
from typing import Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

AMAP_SHARE_API_URL = "https://m5.amap.com/ws/user/route/share/info"


def mask_token(token: str) -> str:
    """脱敏令牌，避免在日志中打印完整敏感信息"""
    if not token:
        return ""
    if len(token) <= 12:
        return "***"
    return f"{token[:4]}...{token[-4:]} (长度: {len(token)})"


def parse_back_schema(back_schema: str) -> Optional[Tuple[float, float]]:
    """
    从 backSchema (例如 amapuri://route/plan?sid=&slat=...&dlat=24.6583&dlon=118.2384) 中解析终点
    支持参数乱序
    """
    if not back_schema:
        return None
    decoded = urllib.parse.unquote(back_schema)
    m_dlon = re.search(r"(?:^|[?&])dlon=([0-9.-]+)", decoded)
    m_dlat = re.search(r"(?:^|[?&])dlat=([0-9.-]+)", decoded)
    if m_dlon and m_dlat:
        try:
            lon = float(m_dlon.group(1))
            lat = float(m_dlat.group(1))
            return lon, lat
        except ValueError:
            pass
    return None


def fetch_amap_share_info(
    token: str,
    timeout: float = 5.0,
    max_retries: int = 2
) -> Tuple[float, float, str]:
    """
    通过高德分享接口获取终点经纬度 (GCJ-02)
    token: 原始或解析后的 urlParameter 令牌字符
    返回: (lon, lat, 'amap_share_api')
    异常:
        ValueError: 接口返回错误码、未找到终点或字段缺失
        TimeoutError: 请求超时
        ConnectionError: 网络连接失败
    """
    # 处理 token 编码：如果 token 已经是百分号编码（例如含 %2B），先单次解码为原始字节串/字符串，
    # 确保像 '+' 不会被错误转换为空格，同时避免二次编码。
    # 如果 token 没有 %，直接使用。
    if "%" in token:
        # 使用 unquote 保留原本代表 '+' 的字符或未编码字符
        clean_token = urllib.parse.unquote(token)
    else:
        clean_token = token

    masked = mask_token(clean_token)
    logger.info("请求高德分享接口解析令牌: %s", masked)

    # 构造请求 URL，确保 param 严格进行标准的 URL 百分号编码 (特别保留 + 为 %2B)
    encoded_param = urllib.parse.quote(clean_token, safe="")
    req_url = f"{AMAP_SHARE_API_URL}?param={encoded_param}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            if requests is not None:
                resp = requests.get(req_url, headers=headers, timeout=timeout)
                status_code = resp.status_code
                text_content = resp.text
            else:
                # 使用标准库 urllib.request 作为备选，无需外部依赖
                req = urllib.request.Request(req_url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    status_code = response.status
                    text_content = response.read().decode("utf-8", errors="replace")

            if status_code != 200:
                raise ConnectionError(f"高德分享接口 HTTP 状态码异常: {status_code}")

            try:
                data_json = json.loads(text_content)
            except Exception as e:
                raise ValueError(f"高德分享接口响应非合法 JSON: {e}")

            # 校验响应结构
            code = str(data_json.get("code", ""))
            data = data_json.get("data")
            if code != "1" or not isinstance(data, dict):
                msg = data_json.get("message") or data_json.get("msg") or f"错误码: {code}"
                raise ValueError(f"高德分享接口返回失败: {msg}")

            # 提取 endPointLon 与 endPointLat
            end_lon = data.get("endPointLon")
            end_lat = data.get("endPointLat")

            if end_lon and end_lat:
                try:
                    lon = float(end_lon)
                    lat = float(end_lat)
                    return lon, lat, "amap_share_api"
                except ValueError:
                    pass

            # 备选提取: backSchema
            back_schema = data.get("backSchema")
            if back_schema:
                coords = parse_back_schema(back_schema)
                if coords:
                    return coords[0], coords[1], "amap_share_api_backschema"

            raise ValueError("高德分享接口响应中未包含有效终点坐标 (endPointLon/endPointLat 或 backSchema)")

        except (requests.exceptions.Timeout if requests else TimeoutError) as e:
            last_error = TimeoutError(f"请求高德分享接口超时 ({timeout}s) [尝试 {attempt}/{max_retries}]")
            logger.warning(str(last_error))
        except (requests.exceptions.RequestException if requests else urllib.error.URLError) as e:
            last_error = ConnectionError(f"连接高德分享接口失败: {e} [尝试 {attempt}/{max_retries}]")
            logger.warning(str(last_error))
        except ValueError as e:
            # 业务层错误不重试
            raise e
        except Exception as e:
            last_error = e
            logger.warning("请求高德接口未知异常: %s", e)

    if last_error:
        raise last_error
    raise ConnectionError("请求高德分享接口失败 (已达最大重试次数)")
