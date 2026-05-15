import sys
import traceback
from datetime import datetime
from rich import inspect
from rich.console import Console
from utils import get_current_date_str
from pathlib import Path

_console = Console()
_log_file = "log/server.log"  # 默认日志文件名
_BASIC_TYPES = (int, float, str, bool, bytes, type(None), list, tuple, dict, set)

# ==========================================
# 配置函数（可选）
# ==========================================
def set_log_file(file_path):
    """如果需要修改默认的日志文件路径，在主程序入口调用一次即可"""
    global _log_file
    _log_file = file_path

# ==========================================
# 内部辅助函数
# ==========================================
def _write_to_file(plain_text):
    """将纯文本追加写入本地日志文件"""
    time_str = get_current_date_str()
    
    # 自动获取文件的父级目录（即 log 文件夹），如果不存在就创建它
    log_path = Path(_log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{time_str}] {plain_text}\n")

# ==========================================
# 导出的核心全局函数
# ==========================================
def log(data, level="info", show_traceback=False, methods=False):
    """
    统一的智能日志打印接口
    :param data: 要打印的内容（字符串、基础变量、或复杂对象）
    :param level: 日志级别 (info, error, success, warn)
    :param show_traceback: 是否在 error 级别打印异常堆栈
    :param methods: 当触发 inspect 检查对象时，是否显示对象的方法
    """
    level = level.upper()
    
    styles = {
        "INFO": "bold cyan",
        "SUCCESS": "bold green",
        "ERROR": "bold red",
        "WARN": "bold yellow"
    }
    style = styles.get(level, "bold white")
    
    # 场景 1：基础数据类型或纯文本日志
    if isinstance(data, _BASIC_TYPES):
        # 控制台输出
        _console.print(f"[{style}]{level}[/{style}] | {data}")
        # 文件输出
        _write_to_file(f"[{level}] | {data}")
        
        # 处理错误堆栈
        if level == "ERROR" and show_traceback:
            if sys.exc_info()[0] is not None:
                _console.print_exception()
                tb_str = "".join(traceback.format_exc())
                _write_to_file(f"[{level}] | Traceback details:\n{tb_str}")
            else:
                _console.print(f"[{styles['WARN']}]WARN[/{styles['WARN']}] | 尝试打印堆栈失败：当前没有活跃的异常")
                _write_to_file("[WARN] | 尝试打印堆栈失败：当前没有活跃的异常")
                
    # 场景 2：复杂对象（触发 inspect）
    else:
        obj_name = type(data).__name__
        prefix_msg = f"开始检查对象 -> {obj_name}"
        
        # 控制台输出
        _console.print(f"[{style}]{level}[/{style}] | [bold yellow]{prefix_msg}[/bold yellow]")
        inspect(data, methods=methods)
        
        # 文件输出
        obj_dict = vars(data) if hasattr(data, '__dict__') else str(data)
        _write_to_file(f"[{level}] | {prefix_msg} | 数据: {obj_dict}")