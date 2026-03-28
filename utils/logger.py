# utils/logger.py - 日志系统
import logging
import sys
from pathlib import Path
from datetime import datetime

_logger = None
_qt_handler = None
_log_messages = []  # 内存缓存，供 UI 显示


class _MemHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        _log_messages.append(msg)
        if len(_log_messages) > 500:
            _log_messages.pop(0)


def setup(log_dir: Path = None):
    global _logger, _qt_handler
    if _logger is not None:
        return _logger

    if log_dir is None:
        from utils import config as cfg
        log_dir = cfg.get_config_dir() / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    log_file = log_dir / f'{today}.log'

    _logger = logging.getLogger('ClassroomTimer')
    _logger.setLevel(logging.DEBUG)
    _logger.handlers.clear()

    # 文件 handler
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', '%H:%M:%S')
    fh.setFormatter(fmt)
    _logger.addHandler(fh)

    # 内存 handler
    mh = _MemHandler()
    mh.setFormatter(fmt)
    _logger.addHandler(mh)

    # 控制台 handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    _logger.addHandler(ch)

    _logger.info('=== 日志系统启动 ===')
    return _logger


def get() -> logging.Logger:
    global _logger
    if _logger is None:
        return setup()
    return _logger


def info(msg): get().info(msg)
def warning(msg): get().warning(msg)
def error(msg): get().error(msg)
def debug(msg): get().debug(msg)


def get_recent(n=100):
    """返回最近 n 条日志"""
    return list(_log_messages[-n:])
