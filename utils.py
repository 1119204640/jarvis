from datetime import datetime, timedelta, timezone
from rich import print
from rich.console import Console
import sys

BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    return datetime.now(BEIJING_TZ)

def format_time(dt_obj):
    return dt_obj.strftime("%Y-%m-%d %H:%M:%S")


# 日志打印功能
console = Console()

def _log(msg, style, prefix):
    print(f"[{style}]{prefix}[/{style}] | {msg}")

# 导出给外部使用的函数
def log_error(msg, show_traceback=False):
    _log(msg, "bold red", "ERROR")
    if show_traceback:
        if sys.exc_info()[0] is not None:   # 只有当确实有异常信息时，才尝试打印堆栈
            console.print_exception()
        else:
            _log("尝试打印堆栈失败：当前没有活跃的异常", "yellow", "WARN")

def log_info(msg):
    _log(msg, "bold cyan", "INFO")

def log_success(msg):
    _log(msg, "bold green", "SUCCESS")