from datetime import datetime, timedelta, timezone
from rich import print
from rich.console import Console

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
        console.print_exception()

def log_info(msg):
    _log(msg, "bold cyan", "INFO")

def log_success(msg):
    _log(msg, "bold green", "SUCCESS")

# 使用示例
log_success("代码同步完成")
log_error("数据库连接失败", show_traceback=True)