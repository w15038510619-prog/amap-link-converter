# -*- coding: utf-8 -*-
"""
历史转换任务持久化与查询模块
保存在 ~/.amap_link_converter/history.json 中
"""

import json
import logging
import os
from typing import List, Dict, Any

from core.template_manager import get_config_dir

logger = logging.getLogger(__name__)


def get_history_file_path() -> str:
    return os.path.join(get_config_dir(), "history.json")


class HistoryManager:
    MAX_ITEMS = 100

    @classmethod
    def load(cls) -> List[Dict[str, Any]]:
        path = get_history_file_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            logger.warning("加载历史记录失败: %s", e)
            return []

    @classmethod
    def add(cls, item: Dict[str, Any]):
        items = cls.load()
        items.insert(0, item)
        # 截断最大数量
        if len(items) > cls.MAX_ITEMS:
            items = items[:cls.MAX_ITEMS]
        cls._save(items)

    @classmethod
    def clear(cls):
        cls._save([])

    @classmethod
    def _save(cls, items: List[Dict[str, Any]]):
        path = get_history_file_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存历史记录失败: %s", e)
