#!/usr/bin/env python3
"""
Git 分支管理工具 - 集合切换分支和合并操作
"""

import os
import subprocess
import sys
import re

# ============== 颜色定义 ==============


class Color:
    """ANSI 颜色代码"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 前景色
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    # 亮色
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


def colorize(text, color):
    """给文本添加颜色"""
    return f"{color}{text}{Color.RESET}"


def bold(text):
    return colorize(text, Color.BOLD)


def success(text):
    return colorize(f"✓ {text}", Color.BRIGHT_GREEN)


def error(text):
    return colorize(f"✗ {text}", Color.BRIGHT_RED)


def warning(text):
    return colorize(f"⚠ {text}", Color.BRIGHT_YELLOW)


def info(text):
    return colorize(f"● {text}", Color.BRIGHT_CYAN)


def dim(text):
    return colorize(text, Color.GRAY)


# ============== 界面输出 ==============


def print_banner():
    """打印横幅"""
    pass


def print_header(title):
    """打印标题"""
    print(f"\n{Color.BRIGHT_BLUE}┌──────────────────────────────────────────────────────────┐{Color.RESET}")
    print(f"{Color.BRIGHT_BLUE}│{Color.RESET}  {Color.BOLD}{Color.WHITE}{title}{Color.RESET}")
    print(f"{Color.BRIGHT_BLUE}└──────────────────────────────────────────────────────────┘{Color.RESET}\n")


def print_separator():
    """打印分隔线"""
    print(f"{Color.GRAY}  {'─' * 56}{Color.RESET}")


def print_repo_status(repo_name, branch, status):
    """打印仓库状态行"""
    if status == "clean":
        status_color = Color.GREEN
        status_icon = "●"
    else:
        status_color = Color.YELLOW
        status_icon = "◆"

    print(f"  {Color.GRAY}│{Color.RESET}  {Color.BOLD}{repo_name:<20}{Color.RESET}  "
          f"{Color.CYAN}分支:{branch:<16}{Color.RESET}  "
          f"{status_color}{status_icon} {status}{Color.RESET}")


def print_result(repo_name, success_flag, message=""):
    """打印操作结果"""
    if success_flag:
        icon = colorize("✓", Color.BRIGHT_GREEN)
        msg = colorize(message, Color.GREEN) if message else ""
    else:
        icon = colorize("✗", Color.BRIGHT_RED)
        msg = colorize(message, Color.RED) if message else ""

    print(f"  {Color.GRAY}│{Color.RESET}  {icon} {Color.BOLD}{repo_name:<20}{Color.RESET}  {msg}")


# ============== Git 操作 ==============

GIT_CMD = None


def get_git_cmd():
    """根据当前路径判断使用哪个 git 命令"""
    global GIT_CMD
    if GIT_CMD is not None:
        return GIT_CMD

    cwd = os.getcwd()
    if cwd.startswith("/mnt/"):
        GIT_CMD = "/mnt/d/git/cmd/git.exe"
    else:
        GIT_CMD = "git"
    return GIT_CMD


def run_git(args, cwd=None):
    """执行 git 命令"""
    cmd = [get_git_cmd()] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def get_submodules():
    """获取所有子模块路径"""
    submodules = []
    gitmodules_path = ".gitmodules"

    if not os.path.exists(gitmodules_path):
        return submodules

    with open(gitmodules_path, "r", encoding="utf-8") as f:
        current_path = None
        for line in f:
            line = line.strip()
            if line.startswith("path"):
                current_path = line.split("=", 1)[1].strip()
                if current_path and os.path.exists(current_path):
                    submodules.append(current_path)
    return submodules


def get_all_repos():
    """获取主仓库和所有子仓库"""
    repos = ["."]
    repos.extend(get_submodules())
    return repos


def has_branch(branch_name, repo_path="."):
    """检查仓库是否有指定分支"""
    code, out, _ = run_git(["branch", "--list", branch_name], cwd=repo_path)
    if branch_name in out:
        return True

    code, out, _ = run_git(["branch", "-r", "--list", f"origin/{branch_name}"], cwd=repo_path)
    return f"origin/{branch_name}" in out


def get_current_branch(repo_path="."):
    """获取当前分支名"""
    code, out, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    return out if code == 0 else "unknown"


def get_repo_name(repo_path):
    """获取仓库显示名称"""
    if repo_path == ".":
        return "主仓库"
    return os.path.basename(repo_path)


def parse_pull_output(output):
    """解析 pull 输出，提取提交数量"""
    # 匹配类似 "Updating abc1234..def5678" 或 "Fast-forward" 后面的文件统计
    # 或者匹配 "X files changed, Y insertions(+), Z deletions(-)"

    commits = 0
    files_changed = 0
    insertions = 0
    deletions = 0

    # 尝试匹配 "Updating xxx..yyy" 获取 commit 数量
    update_match = re.search(r"Updating\s+(\w+)\.\.(\w+)", output)
    if update_match:
        # 使用 rev-list 计算 commit 数量
        code, count, _ = run_git(["rev-list", "--count", f"{update_match.group(1)}..{update_match.group(2)}"])
        if code == 0 and count.isdigit():
            commits = int(count)

    # 匹配文件变更统计
    stat_match = re.search(r"(\d+) files? changed(?:, (\d+) insertions?)?(?:\(\+\))?(?:, (\d+) deletions?)?\(-\)?", output)
    if stat_match:
        files_changed = int(stat_match.group(1))
        insertions = int(stat_match.group(2)) if stat_match.group(2) else 0
        deletions = int(stat_match.group(3)) if stat_match.group(3) else 0

    # 如果没有匹配到，尝试从 "Already up to date" 判断
    if "Already up to date" in output or "Already up-to-date" in output:
        return 0, 0, 0, 0, True  # is_up_to_date = True

    return commits, files_changed, insertions, deletions, False


# ============== SLN 文件处理 ==============


# 需要注释/取消注释的项目行标识
POLYGON_PROJECT_NAME = "SEM_PolygonCtrlLib"
SLN_FILE = "Ui.sln"


def toggle_polygon_in_sln(enable):
    """
    在 Ui.sln 中启用或禁用 SEM_PolygonCtrlLib 项目
    enable=True: 取消注释（启用）
    enable=False: 注释（禁用）
    """
    if not os.path.exists(SLN_FILE):
        print(f"  {warning('未找到 ' + SLN_FILE)}")
        return

    with open(SLN_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    skip_next_end = False
    changed = False

    for line in lines:
        stripped = line.strip()

        # 检查是否是目标 Project 行（包含项目名）
        if POLYGON_PROJECT_NAME in line and ("Project" in stripped or "#Project" in stripped):
            if enable:
                # 取消注释：去掉行首的 #
                if stripped.startswith("#"):
                    new_line = line.replace("#", "", 1)
                    changed = True
                else:
                    new_line = line
                new_lines.append(new_line)
                skip_next_end = True
            else:
                # 注释：在行首添加 #
                if not stripped.startswith("#"):
                    new_lines.append("#" + line)
                    changed = True
                else:
                    new_lines.append(line)
                skip_next_end = True
        elif skip_next_end and ("EndProject" in stripped or "#EndProject" in stripped):
            if enable:
                # 取消注释
                if stripped.startswith("#"):
                    new_line = line.replace("#", "", 1)
                    changed = True
                else:
                    new_line = line
                new_lines.append(new_line)
            else:
                # 注释
                if not stripped.startswith("#"):
                    new_lines.append("#" + line)
                    changed = True
                else:
                    new_lines.append(line)
            skip_next_end = False
        else:
            new_lines.append(line)

    if changed:
        with open(SLN_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        action = "启用" if enable else "禁用"
        print(f"  {colorize('●', Color.CYAN)} 已{action} {colorize('SEM_PolygonCtrlLib', Color.YELLOW)} 项目")
    else:
        print(f"  {colorize('●', Color.GRAY)} SEM_PolygonCtrlLib 项目状态未变化")


# ============== 功能实现 ==============


def stash_all():
    """搁置所有修改（只搁置子仓库）"""
    print_header("搁置所有修改")

    repos = get_submodules()
    stashed_count = 0

    for repo in repos:
        repo_name = get_repo_name(repo)
        code, out, _ = run_git(["status", "--porcelain"], cwd=repo)
        if not out:
            print_result(repo_name, True, dim("无修改，跳过"))
            continue

        # 计算修改文件数
        file_count = len([l for l in out.split("\n") if l.strip()])
        code, out, err = run_git(["stash", "push", "-m", "git_tool: auto stash"], cwd=repo)
        if code == 0:
            print_result(repo_name, True, f"已搁置 {colorize(str(file_count), Color.YELLOW)} 个文件")
            stashed_count += 1
        else:
            print_result(repo_name, False, err)

    print(f"\n  {colorize('→', Color.CYAN)} 完成，共搁置 {colorize(str(stashed_count), Color.BOLD)} 个仓库")


def stash_pop():
    """恢复搁置的修改"""
    print_header("恢复搁置的修改")

    repos = get_all_repos()
    restored_count = 0

    for repo in repos:
        repo_name = get_repo_name(repo)
        code, out, _ = run_git(["stash", "list"], cwd=repo)
        if not out:
            print_result(repo_name, True, dim("无搁置内容，跳过"))
            continue

        code, out, err = run_git(["stash", "pop"], cwd=repo)
        if code == 0:
            print_result(repo_name, True, "已恢复")
            restored_count += 1
        else:
            print_result(repo_name, False, err)

    print(f"\n  {colorize('→', Color.CYAN)} 完成，共恢复 {colorize(str(restored_count), Color.BOLD)} 个仓库")


def sync_remote():
    """同步所有仓库的远程更新（拉取并合并）"""
    print_header("同步远程更新 (Pull)")

    repos = get_all_repos()
    total_commits = 0
    total_files = 0
    success_count = 0

    for repo in repos:
        repo_name = get_repo_name(repo)
        current = get_current_branch(repo)

        # 先 fetch
        run_git(["fetch", "--all", "--prune"], cwd=repo)

        # pull
        code, out, err = run_git(["pull", "origin", current], cwd=repo)
        output = out + "\n" + err

        if code == 0:
            commits, files, insertions, deletions, up_to_date = parse_pull_output(output)

            if up_to_date:
                print_result(repo_name, True, f"{colorize(current, Color.CYAN)} - 已是最新")
            else:
                total_commits += commits
                total_files += files

                # 构建统计信息
                stats = []
                if commits > 0:
                    stats.append(f"{colorize(str(commits), Color.BRIGHT_GREEN)} 个提交")
                if files > 0:
                    stats.append(f"{colorize(str(files), Color.BRIGHT_YELLOW)} 个文件")
                if insertions > 0:
                    stats.append(f"{colorize('+' + str(insertions), Color.GREEN)}")
                if deletions > 0:
                    stats.append(f"{colorize('-' + str(deletions), Color.RED)}")

                stats_str = ", ".join(stats)
                print_result(repo_name, True, f"{colorize(current, Color.CYAN)} - 拉取了 {stats_str}")

            success_count += 1
        else:
            if "CONFLICT" in output:
                print_result(repo_name, False, f"{colorize(current, Color.CYAN)} - 有冲突!")
            else:
                print_result(repo_name, False, err)

    print()
    print_separator()
    print(f"  {colorize('→', Color.CYAN)} 同步完成: "
          f"{colorize(str(success_count), Color.BOLD)} 个仓库, "
          f"共 {colorize(str(total_commits), Color.BRIGHT_GREEN)} 个提交, "
          f"{colorize(str(total_files), Color.BRIGHT_YELLOW)} 个文件变更")


def switch_to_absem():
    """将所有子仓库切换到 ABSEM 分支"""
    print_header("子仓库切换到 ABSEM 分支")

    submodules = get_submodules()
    if not submodules:
        print(f"  {warning('未找到子模块')}")
        return

    switched_count = 0

    for repo in submodules:
        repo_name = get_repo_name(repo)

        if not has_branch("ABSEM", repo):
            print_result(repo_name, True, dim("无 ABSEM 分支，跳过"))
            continue

        # 直接切换，不 fetch
        code, out, _ = run_git(["branch", "--list", "ABSEM"], cwd=repo)
        if "ABSEM" in out:
            code, out, err = run_git(["checkout", "ABSEM"], cwd=repo)
        else:
            code, out, err = run_git(["checkout", "-b", "ABSEM", "origin/ABSEM"], cwd=repo)

        if code == 0:
            print_result(repo_name, True, f"已切换到 {colorize('ABSEM', Color.BRIGHT_MAGENTA)}")
            switched_count += 1
        else:
            print_result(repo_name, False, err)

    # ABSEM 分支启用 PolygonCtrlLib
    print()
    toggle_polygon_in_sln(enable=True)

    print(f"\n  {colorize('→', Color.CYAN)} 完成，共切换 {colorize(str(switched_count), Color.BOLD)} 个仓库")


def switch_to_master():
    """将所有仓库切换到 master 分支"""
    print_header("所有仓库切换到 master 分支")

    repos = get_all_repos()
    switched_count = 0

    for repo in repos:
        repo_name = get_repo_name(repo)

        if not has_branch("master", repo):
            print_result(repo_name, True, dim("无 master 分支，跳过"))
            continue

        # 直接切换，不 fetch
        code, out, _ = run_git(["branch", "--list", "master"], cwd=repo)
        if "master" in out:
            code, out, err = run_git(["checkout", "master"], cwd=repo)
        else:
            code, out, err = run_git(["checkout", "-b", "master", "origin/master"], cwd=repo)

        if code == 0:
            print_result(repo_name, True, f"已切换到 {colorize('master', Color.BRIGHT_GREEN)}")
            switched_count += 1
        else:
            print_result(repo_name, False, err)

    # master 分支禁用 PolygonCtrlLib
    print()
    toggle_polygon_in_sln(enable=False)

    print(f"\n  {colorize('→', Color.CYAN)} 完成，共切换 {colorize(str(switched_count), Color.BOLD)} 个仓库")


def sync_master_to_absem():
    """将 master 分支的修改同步到 ABSEM 分支"""
    print_header("同步 master 到 ABSEM")

    # 排除的仓库（冲突较大，不合并）
    EXCLUDE_REPOS = ["SEM_UI_CCDViewer"]

    repos = get_all_repos()
    active_repos = []

    # 显示当前状态
    print(f"  {colorize('●', Color.CYAN)} 检查仓库状态...\n")

    for repo in repos:
        repo_name = get_repo_name(repo)
        current = get_current_branch(repo)

        # 跳过排除的仓库
        if repo_name in EXCLUDE_REPOS:
            print_result(repo_name, True, dim("已排除，跳过"))
            continue

        if not has_branch("ABSEM", repo):
            print_result(repo_name, True, dim("无 ABSEM 分支，跳过"))
            continue

        if current != "ABSEM":
            print_result(repo_name, True, f"当前 {colorize(current, Color.YELLOW)}，需切换")
        else:
            print_result(repo_name, True, f"已在 {colorize('ABSEM', Color.BRIGHT_MAGENTA)}")

        active_repos.append(repo)

    if not active_repos:
        print(f"\n  {warning('没有需要同步的仓库')}")
        return

    print()
    print_separator()
    print(f"\n  {colorize('●', Color.CYAN)} 开始同步...\n")

    has_conflict = False
    success_count = 0

    for repo in active_repos:
        repo_name = get_repo_name(repo)
        current = get_current_branch(repo)

        # 确保在 ABSEM 分支
        if current != "ABSEM":
            code, out, err = run_git(["checkout", "ABSEM"], cwd=repo)
            if code != 0:
                print_result(repo_name, False, f"无法切换到 ABSEM: {err}")
                has_conflict = True
                continue
            # 切到 ABSEM 时启用 PolygonCtrlLib
            toggle_polygon_in_sln(enable=True)

        # fetch
        run_git(["fetch", "origin"], cwd=repo)

        # merge
        code, out, err = run_git(["merge", "origin/master"], cwd=repo)
        output = out + "\n" + err

        if code == 0:
            commits, files, insertions, deletions, up_to_date = parse_pull_output(output)

            if up_to_date:
                print_result(repo_name, True, f"{colorize('ABSEM', Color.BRIGHT_MAGENTA)} - 已是最新")
            else:
                stats = []
                if commits > 0:
                    stats.append(f"{colorize(str(commits), Color.BRIGHT_GREEN)} 个提交")
                if files > 0:
                    stats.append(f"{colorize(str(files), Color.BRIGHT_YELLOW)} 个文件")
                stats_str = ", ".join(stats) if stats else "合并完成"
                print_result(repo_name, True, f"{colorize('ABSEM', Color.BRIGHT_MAGENTA)} - {stats_str}")

            success_count += 1
        else:
            if "CONFLICT" in output:
                print_result(repo_name, False, "有冲突，请手动解决!")
                has_conflict = True
            else:
                print_result(repo_name, False, err)
                has_conflict = True

    print()
    print_separator()
    if has_conflict:
        print(f"\n  {warning('存在冲突，请手动解决后重新运行此功能')}")
    else:
        print(f"\n  {colorize('→', Color.CYAN)} 同步完成，共 {colorize(str(success_count), Color.BOLD)} 个仓库")


def copy_to_f_drive():
    """一键复制到 F 盘（增量复制，排除 bin/obj/.vs/.idea/.git）"""
    print_header("复制到 F 盘")

    src = os.getcwd()
    dst = "F:\\sem"

    if not os.path.exists(dst):
        print(f"  {error('F 盘不存在')}")
        return

    print(f"  {info('源目录:')} {Color.WHITE}{src}{Color.RESET}")
    print(f"  {info('目标:')}   {Color.WHITE}{dst}{Color.RESET}")
    print(f"  {info('排除:')}   {Color.GRAY}bin/ obj/ .vs/ .idea/ .git/{Color.RESET}")
    print()

    # 使用 robocopy 实现增量复制
    # /MIR - 镜像（增量同步）
    # /XD - 排除目录
    # /XA:SH - 排除系统和隐藏文件
    # /MT:16 - 16线程并行
    cmd = [
        "robocopy", src, dst,
        "/MIR",
        "/XD", "bin", "obj", ".vs", ".idea", ".git", "$RECYCLE.BIN",
        "/XA:SH",
        "/MT:16"
    ]

    print(f"  {info('开始同步...')}\n")

    try:
        result = subprocess.run(cmd)

        # robocopy 返回值: 0=无变化, 1=有复制, 2=有额外, 4=有不匹配, 8=有失败
        print()
        if result.returncode < 4:
            if result.returncode == 0:
                print(f"  {success('完成 - 所有文件已是最新，无需复制')}")
            else:
                print(f"  {success('完成 - 已同步更新')}")
        else:
            print(f"  {error('复制过程有错误')}")

    except Exception as e:
        print(f"\n  {error('执行失败: ' + str(e))}")

    print(f"\n  {colorize('→', Color.CYAN)} 复制完成")


def copy_from_f_drive():
    """一键从 F 盘同步到 E:\\work\\sem（增量复制，排除 bin/obj/.vs/.idea/.git）"""
    print_header("从 F 盘同步")

    src = "F:\\sem"
    dst = "E:\\work\\sem"

    if not os.path.exists(src):
        print(f"  {error('F 盘 sem 目录不存在')}")
        return

    print(f"  {info('源目录:')} {Color.WHITE}{src}{Color.RESET}")
    print(f"  {info('目标:')}   {Color.WHITE}{dst}{Color.RESET}")
    print(f"  {info('排除:')}   {Color.GRAY}bin/ obj/ .vs/ .idea/ .git/{Color.RESET}")
    print()

    # 使用 robocopy 实现增量复制
    # /MIR - 镜像（增量同步）
    # /XD - 排除目录
    # /XA:SH - 排除系统和隐藏文件
    # /MT:16 - 16线程并行
    cmd = [
        "robocopy", src, dst,
        "/MIR",
        "/XD", "bin", "obj", ".vs", ".idea", ".git", "$RECYCLE.BIN",
        "/XA:SH",
        "/MT:16"
    ]

    print(f"  {info('开始同步...')}\n")

    try:
        result = subprocess.run(cmd)

        # robocopy 返回值: 0=无变化, 1=有复制, 2=有额外, 4=有不匹配, 8=有失败
        print()
        if result.returncode < 4:
            if result.returncode == 0:
                print(f"  {success('完成 - 所有文件已是最新，无需复制')}")
            else:
                print(f"  {success('完成 - 已同步更新')}")
        else:
            print(f"  {error('同步过程有错误')}")

    except Exception as e:
        print(f"\n  {error('执行失败: ' + str(e))}")

    print(f"\n  {colorize('→', Color.CYAN)} 同步完成")


def show_status():
    """显示所有仓库状态"""
    print_header("仓库状态总览")

    repos = get_all_repos()

    # 表头
    print(f"  {Color.GRAY}┌────────────────────────────────────────────────────────────┐{Color.RESET}")
    print(f"  {Color.GRAY}│{Color.RESET}  {Color.BOLD}{'仓库':<18}{Color.RESET}  {Color.BOLD}{'分支':<16}{Color.RESET}  {Color.BOLD}{'状态':<12}{Color.RESET}  {Color.BOLD}{'搁置':<6}{Color.RESET}  {Color.GRAY}│{Color.RESET}")
    print(f"  {Color.GRAY}├────────────────────────────────────────────────────────────┤{Color.RESET}")

    for repo in repos:
        repo_name = get_repo_name(repo)
        current = get_current_branch(repo)

        # 检查修改状态
        code, out, _ = run_git(["status", "--porcelain"], cwd=repo)
        if out:
            file_count = len([l for l in out.split("\n") if l.strip()])
            status = colorize(f"{file_count} 个修改", Color.YELLOW)
            status_icon = "◆"
        else:
            status = colorize("干净", Color.GREEN)
            status_icon = "●"

        # 检查搁置数量
        code, stash_out, _ = run_git(["stash", "list"], cwd=repo)
        stash_count = len([l for l in stash_out.split("\n") if l.strip()]) if stash_out else 0
        stash_str = colorize(str(stash_count), Color.YELLOW) if stash_count > 0 else dim("0")

        print(f"  {Color.GRAY}│{Color.RESET}  {Color.BOLD}{repo_name:<18}{Color.RESET}  "
              f"{Color.CYAN}{current:<16}{Color.RESET}  "
              f"{status_icon} {status:<20}{Color.RESET}  "
              f"{stash_str:<6}  {Color.GRAY}│{Color.RESET}")

    print(f"  {Color.GRAY}└────────────────────────────────────────────────────────────┘{Color.RESET}")

    # 底部信息
    print(f"\n  {dim('提示:')} 使用选项 {colorize('1', Color.BRIGHT_CYAN)} 搁置修改, "
          f"选项 {colorize('2', Color.BRIGHT_CYAN)} 恢复搁置")


# ============== 主菜单 ==============


def print_menu():
    """打印主菜单"""
    print()
    print(f"  {Color.BRIGHT_CYAN}┌─────────────────────────────────────────────────────────────┐{Color.RESET}")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('1', Color.BRIGHT_WHITE)}. 搁置所有修改")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('2', Color.BRIGHT_WHITE)}. 恢复搁置的修改")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('3', Color.BRIGHT_WHITE)}. 同步远程更新 (Pull)")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('4', Color.BRIGHT_WHITE)}. 子仓库切到 ABSEM 分支")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('5', Color.BRIGHT_WHITE)}. 所有仓库切到 master 分支")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('6', Color.BRIGHT_WHITE)}. 同步 master → ABSEM")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('7', Color.BRIGHT_WHITE)}. 显示所有仓库状态")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('8', Color.BRIGHT_WHITE)}. 一键复制到 F 盘")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('9', Color.BRIGHT_WHITE)}. 从 F 盘同步到本地")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}    {colorize('0', Color.BRIGHT_RED)}. 退出")
    print(f"  {Color.BRIGHT_CYAN}│{Color.RESET}")
    print(f"  {Color.BRIGHT_CYAN}└─────────────────────────────────────────────────────────────┘{Color.RESET}")


def main():
    """主函数"""
    # Windows 终端启用 ANSI 颜色支持
    if sys.platform == "win32":
        os.system("")

    # 确保在项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    while True:
        print_banner()
        print_menu()

        choice = input(f"\n  {colorize('▸', Color.BRIGHT_CYAN)} 请输入选项: ").strip()

        if choice == "1":
            stash_all()
        elif choice == "2":
            stash_pop()
        elif choice == "3":
            sync_remote()
        elif choice == "4":
            switch_to_absem()
        elif choice == "5":
            switch_to_master()
        elif choice == "6":
            sync_master_to_absem()
        elif choice == "7":
            show_status()
        elif choice == "8":
            copy_to_f_drive()
        elif choice == "9":
            copy_from_f_drive()
        elif choice == "0":
            print(f"\n  {colorize('👋 再见!', Color.BRIGHT_CYAN)}\n")
            sys.exit(0)
        else:
            print(f"\n  {warning('无效选项，请重新输入')}")

        input(f"\n  {dim('按 Enter 继续...')}")


if __name__ == "__main__":
    main()
