import os
import subprocess
import time
import sys


def check_word_installed():
    """检查 Microsoft Word 是否已安装"""
    result = subprocess.run(
        ['mdfind', 'kMDItemCFBundleIdentifier == "com.microsoft.Word"'],
        capture_output=True, text=True
    )
    if not result.stdout.strip():
        print("❌ 未检测到 Microsoft Word，请先安装。")
        sys.exit(1)
    print("✅ 已检测到 Microsoft Word")


def word_to_pdf_mac_posix(input_folder, output_folder=None):
    if output_folder is None:
        output_folder = os.path.join(input_folder, "PDF输出")

    os.makedirs(output_folder, exist_ok=True)

    # 检查 Word 是否安装
    check_word_installed()

    # 将路径转为绝对路径
    input_folder = os.path.abspath(input_folder)
    output_folder = os.path.abspath(output_folder)

    print("正在启动 Microsoft Word...")
    subprocess.run(
        ['osascript', '-e', 'tell application "Microsoft Word" to activate'],
        check=False
    )
    time.sleep(3)

    word_files = []
    for f in os.listdir(input_folder):
        if f.lower().endswith(('.docx', '.doc')) and not f.startswith('~$'):
            word_files.append(f)

    if not word_files:
        print(f"❌ 在 {input_folder} 中未找到任何 .docx 或 .doc 文件")
        return

    print(f"找到 {len(word_files)} 个 Word 文件")
    converted = 0
    failed = []

    for filename in word_files:
        input_path = os.path.join(input_folder, filename)
        output_filename = os.path.splitext(filename)[0] + ".pdf"
        output_path = os.path.join(output_folder, output_filename)

        print(f"正在转换: {filename}")

        # 使用 HFS 路径格式（Mac 风格），兼容性更好
        # 格式: Macintosh HD:Users:xxx:file.docx
        hfs_input = posix_to_hfs(input_path)
        hfs_output = posix_to_hfs(output_path)

        # 方案1: 使用 SaveAs2 方法（兼容性更好）
        applescript = f'''
        tell application "Microsoft Word"
            try
                open POSIX file "{input_path}"
                delay 1
                set theDoc to active document
                save as theDoc file name "{hfs_output}" file format format PDF
                close theDoc saving no
                return "success"
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=120
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if "success" in stdout:
                # 验证 PDF 文件是否真的生成了
                if os.path.exists(output_path):
                    print(f"  ✅ 成功: {output_filename}")
                    converted += 1
                else:
                    print(f"  ⚠️  Word 报告成功但 PDF 未生成")
                    # 尝试方案2: 使用 export 方法
                    print(f"  🔄 尝试备用方案...")
                    if try_export_method(input_path, output_path, filename):
                        print(f"  ✅ 备用方案成功: {output_filename}")
                        converted += 1
                    else:
                        failed.append(filename)
            else:
                error_msg = stdout or stderr
                print(f"  ❌ 失败: {filename}")
                print(f"     错误信息: {error_msg}")
                # 尝试备用方案
                print(f"  🔄 尝试备用方案...")
                if try_export_method(input_path, output_path, filename):
                    print(f"  ✅ 备用方案成功: {output_filename}")
                    converted += 1
                else:
                    failed.append(filename)

        except subprocess.TimeoutExpired:
            print(f"  ❌ 超时: {filename}")
            failed.append(filename)
        except Exception as e:
            print(f"  ❌ 异常: {filename} - {str(e)}")
            failed.append(filename)

    # 关闭所有已打开的文档
    print("\n正在关闭所有已打开的文档...")
    subprocess.run(
        ['osascript', '-e',
         'tell application "Microsoft Word" to close every document saving no'],
        check=False
    )
    time.sleep(1)

    print("\n" + "=" * 50)
    print(f"✅ 成功转换: {converted} 个文件")
    print(f"❌ 转换失败: {len(failed)} 个文件")
    if failed:
        print(f"失败列表: {', '.join(failed)}")
    print(f"📁 输出位置: {output_folder}")


def posix_to_hfs(posix_path):
    """将 POSIX 路径转换为 HFS 路径（Mac 风格路径）"""
    result = subprocess.run(
        ['osascript', '-e',
         f'POSIX file "{posix_path}" as text'],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def try_export_method(input_path, output_path, filename):
    """备用方案：使用 Word 的 export/另存为功能"""
    hfs_output = posix_to_hfs(output_path)

    # 尝试不同的 AppleScript 语法
    applescripts = [
        # 方案A: 使用 docx-saveas 的完整语法
        f'''
        tell application "Microsoft Word"
            try
                set theDoc to active document
                save as theDoc file name "{hfs_output}" file format format document17
                close theDoc saving no
                return "success"
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        ''',
        # 方案B: 使用 print to PDF（通过系统打印功能）
        f'''
        tell application "Microsoft Word"
            try
                set theDoc to active document
                print out theDoc
                delay 2
                close theDoc saving no
                return "success"
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        ''',
    ]

    for i, script in enumerate(applescripts):
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=60
            )
            if "success" in result.stdout and os.path.exists(output_path):
                return True
        except Exception:
            continue

    return False


if __name__ == "__main__":
    folder = input("请输入 Word 文件夹路径: ").strip()
    # 支持拖拽文件夹（macOS 拖拽会带引号）
    folder = folder.strip('"').strip("'")
    if not os.path.isdir(folder):
        print(f"❌ 路径不存在: {folder}")
        sys.exit(1)
    word_to_pdf_mac_posix(folder)