import sys
import traceback
from rich import inspect
from rich.console import Console
from utils import get_current_date_str
from pathlib import Path

_console = Console()
_log_file = "log/server.log"  # 默认日志文件名
_BASIC_TYPES = (int, float, str, bool, bytes, type(None))

# 定义一个“哨兵对象”，用来判断用户到底传了几个参数
_NO_PREFIX = object()

def set_log_file(file_path):
    """如果需要修改默认的日志文件路径，在主程序入口调用一次即可"""
    global _log_file
    _log_file = file_path

def _write_to_file(plain_text):
    """将纯文本追加写入本地日志文件"""
    time_str = get_current_date_str()
    
    log_path = Path(_log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{time_str}] {plain_text}\n")

def _resolve_args(arg1, arg2):
    """智能解析参数：如果只传 1 个参数，则视作 data；如果传 2 个，则视为 prefix 和 data"""
    if arg2 is _NO_PREFIX:
        return None, arg1        # 只有 arg1，说明它是 data
    return str(arg1), arg2       # 有两个参数，说明 arg1 是 prefix，arg2 是 data

def _log(data, level="INFO", show_traceback=False, methods=False, depth=2, prefix=None):
    """内部统一的日志处理函数"""
    styles = {
        "INFO": "bold cyan",
        "SUCCESS": "bold green",
        "ERROR": "bold red",
        "WARN": "bold yellow"
    }

    style = styles.get(level, "bold white")
    
    try:
        caller_frame = sys._getframe(depth)
        filename = Path(caller_frame.f_code.co_filename).name
        lineno = caller_frame.f_lineno
        loc = f"{filename}:{lineno}"
    except Exception:
        loc = "unknown:0"
    
    # 处理前缀标签
    prefix_console = f" [bold magenta][{prefix}][/bold magenta]" if prefix else ""
    prefix_file = f" [{prefix}]" if prefix else ""
    
    if isinstance(data, _BASIC_TYPES):
        _console.print(f"[{style}]{level}[/{style}] [dim]({loc})[/dim]{prefix_console} | {data}")
        _write_to_file(f"[{level}] ({loc}){prefix_file} | {data}")
        
        if level == "ERROR" and show_traceback:
            if sys.exc_info()[0] is not None:
                _console.print_exception()
                tb_str = "".join(traceback.format_exc())
                _write_to_file(f"[{level}] | Traceback details:\n{tb_str}")
            else:
                _console.print(f"[{styles['WARN']}]WARN[/{styles['WARN']}] | 尝试打印堆栈失败：当前没有活跃的异常")
                _write_to_file("[WARN] | 尝试打印堆栈失败：当前没有活跃的异常")

    elif isinstance(data, (list, tuple, dict, set)):
        _console.print(f"[{style}]{level}[/{style}] [dim]({loc})[/dim]{prefix_console} | [bold yellow]开始展开集合 -> {type(data).__name__}[/bold yellow]")
        _console.print(data)
        _write_to_file(f"[{level}] ({loc}){prefix_file} | 集合数据: {str(data)}")
                
    else:
        obj_name = type(data).__name__
        prefix_msg = f"开始检查对象 -> {obj_name}"
        
        _console.print(f"[{style}]{level}[/{style}] [dim]({loc})[/dim]{prefix_console} | [bold yellow]{prefix_msg}[/bold yellow]")
        inspect(data, methods=methods)
        
        obj_dict = vars(data) if hasattr(data, '__dict__') else str(data)
        _write_to_file(f"[{level}] ({loc}){prefix_file} | {prefix_msg} | 数据: {obj_dict}")


def info(prefix_or_data, data=_NO_PREFIX, methods=False):
    prefix, actual_data = _resolve_args(prefix_or_data, data)
    _log(actual_data, level="INFO", methods=methods, depth=2, prefix=prefix)

def success(prefix_or_data, data=_NO_PREFIX, methods=False):
    prefix, actual_data = _resolve_args(prefix_or_data, data)
    _log(actual_data, level="SUCCESS", methods=methods, depth=2, prefix=prefix)

def warn(prefix_or_data, data=_NO_PREFIX, methods=False):
    prefix, actual_data = _resolve_args(prefix_or_data, data)
    _log(actual_data, level="WARN", methods=methods, depth=2, prefix=prefix)

def error(prefix_or_data, data=_NO_PREFIX, show_traceback=True, methods=False):
    prefix, actual_data = _resolve_args(prefix_or_data, data)
    _log(actual_data, level="ERROR", show_traceback=show_traceback, methods=methods, depth=2, prefix=prefix)