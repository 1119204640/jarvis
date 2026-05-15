from datetime import datetime, timedelta, timezone
from rich import print
from rich.console import Console
from rich.panel import Panel
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

# 专门用来格式化打印类或对象的详细结构的
def log_object(obj, title="对象结构检查", methods=False):
    """
    格式化打印一个类或对象的属性和方法
    :param obj: 要检查的对象或类
    :param title: 打印面板的标题
    :param methods: 是否同时打印出对象的方法（默认只打印属性）
    """
    _log(f"开始检查元素 -> {type(obj).__name__}", "bold magenta", "INSPECT")
    
    # 利用 rich 内置的 inspect 功能，并将其包裹在一个美观的面板(Panel)里
    console.print(
        Panel(
            f"[bold yellow]类型:[/] {type(obj)}\n", 
            title=f"[bold border]{title}[/]", 
            expand=False
        )
    )
    console.inspect(obj, methods=methods, help=False)