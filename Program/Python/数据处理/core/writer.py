"""
统一文件写入：支持 Excel/CSV/JSON/TXT 等格式
"""
import os
import pandas as pd

from config import OUTPUT_DIR, CLEAN_DIR, logger


def write_file(df: pd.DataFrame, path: str, **kwargs) -> str:
    """统一写入单个文件，根据扩展名自动选择格式

    Args:
        df: 要写入的 DataFrame
        path: 输出路径
        **kwargs: 额外参数 (encoding, index, sheet_name 等)

    Returns:
        实际写入的文件路径
    """
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    ext = os.path.splitext(path)[1].lower()
    index = kwargs.pop('index', False)

    if ext == '.csv':
        encoding = kwargs.pop('encoding', 'utf-8-sig')
        df.to_csv(path, index=index, encoding=encoding, **kwargs)
    elif ext == '.tsv':
        encoding = kwargs.pop('encoding', 'utf-8-sig')
        df.to_csv(path, index=index, encoding=encoding, sep='\t', **kwargs)
    elif ext in ('.xlsx', '.xls'):
        sheet_name = kwargs.pop('sheet_name', 'Sheet1')
        engine = 'openpyxl' if ext == '.xlsx' else None
        df.to_excel(path, index=index, sheet_name=sheet_name, engine=engine, **kwargs)
    elif ext == '.json':
        orient = kwargs.pop('orient', 'records')
        force_ascii = kwargs.pop('force_ascii', False)
        encoding = kwargs.pop('encoding', 'utf-8')
        df.to_json(path, orient=orient, force_ascii=force_ascii, **kwargs)
    elif ext == '.txt':
        encoding = kwargs.pop('encoding', 'utf-8')
        sep = kwargs.pop('sep', '\t')
        df.to_csv(path, index=index, encoding=encoding, sep=sep, **kwargs)
    else:
        raise ValueError(f"不支持的输出格式: {ext}")

    size_kb = os.path.getsize(path) / 1024
    logger.info(f"写入完成: {path} ({size_kb:.1f} KB, {df.shape[0]} 行)")
    return path


def write_multiple(dfs: dict[str, pd.DataFrame], output_dir: str,
                   fmt: str = 'csv', **kwargs) -> list[str]:
    """批量写入多个 DataFrame

    Args:
        dfs: {文件名(不含扩展名): DataFrame} 字典
        output_dir: 输出目录
        fmt: 输出格式 (csv, xlsx, json, txt)
        **kwargs: 传递给 write_file

    Returns:
        写入的文件路径列表
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for name, df in dfs.items():
        path = os.path.join(output_dir, f"{name}.{fmt}")
        write_file(df, path, **kwargs)
        paths.append(path)
    return paths
