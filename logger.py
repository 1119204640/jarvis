import sys
import traceback
from rich import inspect
from rich.console import Console
from utils import get_current_date_str
from pathlib import Path

_console = Console()
_log_file = "log/server.log"  # 默认日志文件名
_BASIC_TYPES = (int, float, str, bool, bytes, type(None))

def set_log_file(file_path):
    """如果需要修改默认的日志文件路径，在主程序入口调用一次即可"""
    global _log_file
    _log_file = file_path

def _write_to_file(plain_text):
    """将纯文本追加写入本地日志文件"""
    time_str = get_current_date_str()
    
    # 自动获取文件的父级目录（即 log 文件夹），如果不存在就创建它
    log_path = Path(_log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{time_str}] {plain_text}\n")

# 私有函数：处理所有核心的打印和写入逻辑
def _log(data, level="INFO", show_traceback=False, methods=False, depth=2):
    """
    内部统一的日志处理函数
    :param depth: 堆栈深度。默认 2 表示跳过当前函数和上一层包装函数，直接获取业务调用处
    """
    styles = {
        "INFO": "bold cyan",
        "SUCCESS": "bold green",
        "ERROR": "bold red",
        "WARN": "bold yellow"
    }

    style = styles.get(level, "bold white")
    
    # 🌟 根据传入的 depth 动态获取调用栈位置
    try:
        caller_frame = sys._getframe(depth)
        filename = Path(caller_frame.f_code.co_filename).name  # 只拿文件名
        lineno = caller_frame.f_lineno
        loc = f"{filename}:{lineno}"
    except Exception:
        loc = "unknown:0"
    
    # 基础数据类型或纯文本日志
    if isinstance(data, _BASIC_TYPES):
        _console.print(f"[{style}]{level}[/{style}] [dim]({loc})[/dim] | {data}")
        _write_to_file(f"[{level}] ({loc}) | {data}")
        
        # 处理错误堆栈
        if level == "ERROR" and show_traceback:
            if sys.exc_info()[0] is not None:
                _console.print_exception()
                tb_str = "".join(traceback.format_exc())
                _write_to_file(f"[{level}] | Traceback details:\n{tb_str}")
            else:
                _console.print(f"[{styles['WARN']}]WARN[/{styles['WARN']}] | 尝试打印堆栈失败：当前没有活跃的异常")
                _write_to_file("[WARN] | 尝试打印堆栈失败：当前没有活跃的异常")

    # 遇到了 List, Dict, Set 等集合结构
    elif isinstance(data, (list, tuple, dict, set)):
        _console.print(f"[{style}]{level}[/{style}] [dim]({loc})[/dim] | [bold yellow]开始展开集合 -> {type(data).__name__}[/bold yellow]")
        _console.print(data)
        _write_to_file(f"[{level}] ({loc}) | 集合数据: {str(data)}")
                
    # 复杂对象（触发 inspect）
    else:
        obj_name = type(data).__name__
        prefix_msg = f"开始检查对象 -> {obj_name}"
        
        _console.print(f"[{style}]{level}[/{style}] [dim]({loc})[/dim] | [bold yellow]{prefix_msg}[/bold yellow]")
        inspect(data, methods=methods)
        
        obj_dict = vars(data) if hasattr(data, '__dict__') else str(data)
        _write_to_file(f"[{level}] ({loc}) | {prefix_msg} | 数据: {obj_dict}")


def info(data, methods=False):
    """打印普通信息日志，支持自动识别集合与对象"""
    _log(data, level="INFO", methods=methods, depth=2)

def success(data, methods=False):
    """打印成功提示日志，支持自动识别集合与对象"""
    _log(data, level="SUCCESS", methods=methods, depth=2)

def warn(data, methods=False):
    """打印警告日志，支持自动识别集合与对象"""
    _log(data, level="WARN", methods=methods, depth=2)

def error(data, show_traceback=True, methods=False):
    """打印错误日志，默认当存在活跃异常时自动打印堆栈信息"""
    _log(data, level="ERROR", show_traceback=show_traceback, methods=methods, depth=2)