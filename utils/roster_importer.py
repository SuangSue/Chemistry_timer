# utils/roster_importer.py - 名单导入工具
import os, shutil
from pathlib import Path
from utils.config import rosters_dir, save_roster


def _stem(path):
    return Path(path).stem


def import_file(src_path):
    """
    从 src_path 导入名单。
    返回 (name_list, roster_name, error_msg)
    """
    path = Path(src_path)
    if not path.exists():
        return [], '', f'文件不存在: {src_path}'
    ext = path.suffix.lower()
    if ext == '.txt':
        names, err = _import_txt(path)
    elif ext in ('.xlsx', '.xls', '.csv'):
        names, err = _import_excel(path)
    else:
        return [], '', f'不支持的文件格式: {ext}'
    if err:
        return [], '', err
    if not names:
        return [], '', '未能从文件中提取到任何姓名'
    roster_name = path.stem
    dest = rosters_dir() / f'_src_{path.name}'
    try:
        shutil.copy2(str(path), str(dest))
    except Exception:
        pass
    save_roster(roster_name, names)
    return names, roster_name, None


def _import_txt(path):
    try:
        text = None
        for enc in ('utf-8', 'utf-8-sig', 'gbk', 'gb18030', 'utf-16'):
            try:
                text = path.read_text(encoding=enc)
                break
            except Exception:
                continue
        if text is None:
            return [], '无法识别文件编码'
        names = [line.strip() for line in text.splitlines() if line.strip()]
        return names, None
    except Exception as e:
        return [], str(e)


def _import_excel(path):
    try:
        ext = path.suffix.lower()
        if ext == '.csv':
            return _import_csv(path)
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
        except ImportError:
            try:
                import xlrd
                wb = xlrd.open_workbook(str(path))
                ws = wb.sheet_by_index(0)
                rows = [ws.row_values(i) for i in range(ws.nrows)]
            except ImportError:
                return [], '需要安装 openpyxl 或 xlrd 库'
        return _extract_names_from_rows(rows)
    except Exception as e:
        return [], str(e)


def _import_csv(path):
    import csv
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'gb18030'):
        try:
            with open(path, encoding=enc, newline='') as f:
                rows = list(csv.reader(f))
            return _extract_names_from_rows(rows)
        except Exception:
            continue
    return [], '无法读取CSV文件'


def _extract_names_from_rows(rows):
    if not rows:
        return [], '表格为空'
    NAME_KEYWORDS = ['姓名', '名字', '学生姓名', 'name', 'student', '学生', '名称']
    header = [str(c).strip().lower() if c else '' for c in rows[0]]
    col_idx = 0
    data_start = 0
    found_header = False
    for kw in NAME_KEYWORDS:
        for i, h in enumerate(header):
            if kw in h:
                col_idx = i
                data_start = 1
                found_header = True
                break
        if found_header:
            break
    if not found_header:
        first = str(rows[0][0]).strip() if rows[0] else ''
        data_start = 0 if (first and not first.isdigit()) else 1
    names = []
    for row in rows[data_start:]:
        if not row:
            continue
        val = str(row[col_idx]).strip() if col_idx < len(row) else ''
        if val and not val.replace('.', '').isdigit() and val not in ('None', 'nan', ''):
            names.append(val)
    return names, None
