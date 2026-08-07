"""
批量处理引擎：扫描文件 → 读取 → 处理 → 输出
支持 glob 模式匹配和并发处理
"""
import os
import glob
from typing import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd

from config import logger
from core.reader import read_file
from core.writer import write_file
from utils.helpers import find_files, get_file_info, print_progress


def batch_process(
    pattern: str,
    operation: Callable[[pd.DataFrame], pd.DataFrame],
    output_dir: str = None,
    concat: bool = False,
    output_fmt: str = 'csv',
    recursive: bool = True,
    parallel: bool = False,
    max_workers: int = 4,
    **read_kwargs
) -> dict:
    """批量处理文件

    Args:
        pattern: 文件匹配模式，如 'data/*.csv' 或 '.xlsx'
        operation: 处理函数，接受 DataFrame 返回 DataFrame
        output_dir: 输出目录 (默认 OUTPUT_DIR/batch_result)
        concat: True=先合并再处理, False=逐文件处理
        output_fmt: 输出格式 (csv/xlsx/json)
        recursive: 是否递归搜索
        parallel: 是否并行处理
        max_workers: 并行进程数
        **read_kwargs: 传递给 read_file

    Returns:
        {'files': [...], 'output_dir': '...', 'total_rows': N}
    """
    # 解析文件列表
    if os.path.sep in pattern or '/' in pattern:
        files = glob.glob(pattern, recursive=recursive)
    else:
        # 扩展名模式
        files = find_files(patterns=[pattern], recursive=recursive)

    if not files:
        logger.warning(f"未找到匹配文件: {pattern}")
        return {'files': [], 'output_dir': output_dir, 'total_rows': 0}

    logger.info(f"批量处理: 找到 {len(files)} 个文件")
    for f in files:
        info = get_file_info(f)
        logger.info(f"  {info['name']} ({info['size_mb']}MB)")

    if output_dir is None:
        from config import OUTPUT_DIR
        output_dir = os.path.join(OUTPUT_DIR, 'batch_result')
    os.makedirs(output_dir, exist_ok=True)

    if concat:
        # 模式A: 全部合并后统一处理
        logger.info("模式: 合并处理")
        all_dfs = []
        for i, f in enumerate(files):
            df = read_file(f, **read_kwargs)
            all_dfs.append(df)
            print_progress(i + 1, len(files), "读取文件")
        combined = pd.concat(all_dfs, ignore_index=True)
        result = operation(combined)
        output_path = os.path.join(output_dir, f"combined_result.{output_fmt}")
        write_file(result, output_path)

        return {
            'files': files,
            'output_dir': output_dir,
            'total_rows': result.shape[0],
            'output_paths': [output_path]
        }

    else:
        # 模式B: 逐文件处理
        logger.info("模式: 逐文件处理")

        if parallel:
            return _batch_parallel(files, operation, output_dir, output_fmt,
                                   max_workers, **read_kwargs)
        else:
            return _batch_sequential(files, operation, output_dir, output_fmt,
                                     **read_kwargs)


def batch_apply(
    files: list[str],
    operation: Callable,
    **read_kwargs
) -> list:
    """对每个文件执行同一操作，返回结果列表

    Args:
        files: 文件路径列表
        operation: 处理函数 (DataFrame) -> Any
    """
    results = []
    for i, f in enumerate(files):
        df = read_file(f, **read_kwargs)
        result = operation(df)
        results.append(result)
        print_progress(i + 1, len(files), "处理文件")
    return results


def _batch_sequential(files, operation, output_dir, output_fmt, **read_kwargs):
    """顺序批量处理"""
    output_paths = []
    total_rows = 0

    for i, f in enumerate(files):
        try:
            df = read_file(f, **read_kwargs)
            result = operation(df)
            base = os.path.splitext(os.path.basename(f))[0]
            output_path = os.path.join(output_dir, f"{base}_processed.{output_fmt}")
            write_file(result, output_path)
            output_paths.append(output_path)
            total_rows += result.shape[0]
            print_progress(i + 1, len(files), "处理文件")
        except Exception as e:
            logger.error(f"处理失败 {f}: {e}")

    print()
    return {
        'files': files,
        'output_dir': output_dir,
        'total_rows': total_rows,
        'output_paths': output_paths
    }


def _batch_parallel(files, operation, output_dir, output_fmt,
                    max_workers, **read_kwargs):
    """并行批量处理"""
    def _process_one(f, idx):
        try:
            df = read_file(f, **read_kwargs)
            result = operation(df)
            base = os.path.splitext(os.path.basename(f))[0]
            out = os.path.join(output_dir, f"{base}_processed.{output_fmt}")
            write_file(result, out)
            return {'path': out, 'rows': result.shape[0], 'error': None}
        except Exception as e:
            return {'path': None, 'rows': 0, 'error': str(e)}

    output_paths = []
    total_rows = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_one, f, i): f
                   for i, f in enumerate(files)}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            if result['error']:
                logger.error(f"处理失败: {result['error']}")
            else:
                output_paths.append(result['path'])
                total_rows += result['rows']
            print_progress(completed, len(files), "处理文件")

    print()
    return {
        'files': files,
        'output_dir': output_dir,
        'total_rows': total_rows,
        'output_paths': output_paths
    }
