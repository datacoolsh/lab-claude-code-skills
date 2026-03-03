#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import yagmail
from dotenv import load_dotenv


def _load_env() -> None:
    """从 .env 文件加载配置（按优先级查找：脚本同目录 > 项目根目录）"""
    script_dir = Path(__file__).resolve().parent
    for candidate in [script_dir / ".env", Path.cwd() / ".env"]:
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return


def _json_print(obj: dict) -> None:
    # Claude/CI 友好：单行 JSON
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _split_multi(values: Optional[List[str]]) -> List[str]:
    """
    支持重复参数：--to a --to b
    也支持逗号分隔：--to a,b
    """
    if not values:
        return []
    out: List[str] = []
    for v in values:
        parts = [p.strip() for p in v.split(",") if p.strip()]
        out.extend(parts)
    return out


def _validate_files(paths: List[str]) -> List[str]:
    files: List[str] = []
    for p in paths:
        fp = Path(p)
        if not fp.exists() or not fp.is_file():
            raise FileNotFoundError(f"attachment_not_found: {p}")
        files.append(str(fp))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="send_mail",
        description="Send email via SMTP using yagmail. Outputs one-line JSON status.",
    )

    # 加载 .env 配置
    _load_env()

    # 邮件内容参数（通过命令行传入）
    parser.add_argument(
        "--to",
        required=True,
        action="append",
        help="Recipient email. Repeatable or comma-separated.",
    )
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--text", required=True, help="Plain text body (required)")
    parser.add_argument("--html", default="", help="HTML body (optional)")
    parser.add_argument(
        "--cc", action="append", help="CC recipient. Repeatable or comma-separated."
    )
    parser.add_argument(
        "--bcc", action="append", help="BCC recipient. Repeatable or comma-separated."
    )
    parser.add_argument(
        "--attach", action="append", default=[], help="Attachment path. Repeatable."
    )

    args = parser.parse_args()

    # SMTP 配置从环境变量读取
    # Gmail 配置说明:
    # - SMTP_HOST: smtp.gmail.com (默认)
    # - SMTP_PORT: 587 (STARTTLS, 推荐) 或 465 (SSL)
    # - SMTP_USER: 你的完整 Gmail 地址 (例如: your_email@gmail.com)
    # - SMTP_PASS: Gmail 应用专用密码 (不是你的 Gmail 密码!)
    #   获取应用专用密码: https://myaccount.google.com/apppasswords
    #   注意: 需要先启用两步验证才能创建应用专用密码
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_timeout = int(os.environ.get("SMTP_TIMEOUT", "30"))

    if not smtp_user or not smtp_pass:
        error_msg = (
            "SMTP_USER and SMTP_PASS must be set in .env or environment variables. "
            "For Gmail: SMTP_USER should be your Gmail address, "
            "SMTP_PASS should be an App Password (not your Gmail password). "
            "Visit https://myaccount.google.com/apppasswords to create one."
        )
        _json_print({"ok": False, "stage": "error", "error_type": "ConfigError",
                      "error": error_msg})
        return 1

    to_list = _split_multi(args.to)
    cc_list = _split_multi(args.cc)
    bcc_list = _split_multi(args.bcc)
    attach_list = _validate_files(args.attach)

    started = time.time()

    # 输出：开始状态（可选，但对流水线日志很友好）
    _json_print(
        {
            "ok": True,
            "stage": "start",
            "to": to_list,
            "cc": cc_list,
            "bcc": bcc_list,
            "subject": args.subject,
            "host": smtp_host,
            "port": smtp_port,
        }
    )

    try:
        # yagmail: 简单 SMTP 封装
        # Gmail 支持两种加密方式:
        # - 端口 587: 使用 STARTTLS (smtp_starttls=True, smtp_ssl=False)
        # - 端口 465: 使用 SSL/TLS (smtp_starttls=False, smtp_ssl=True)
        use_ssl = smtp_port == 465
        yag = yagmail.SMTP(
            user=smtp_user,
            password=smtp_pass,
            host=smtp_host,
            port=smtp_port,
            timeout=smtp_timeout,
            smtp_starttls=not use_ssl,  # 端口 587 启用 STARTTLS
            smtp_ssl=use_ssl,            # 端口 465 启用 SSL
        )

        contents = [args.text]
        if args.html.strip():
            contents.append(yagmail.inline(args.html))  # 让 HTML 以 inline 方式发送

        # yagmail 的 send 支持 to / cc / bcc
        yag.send(
            to=to_list,
            cc=cc_list or None,
            bcc=bcc_list or None,
            subject=args.subject,
            contents=contents,
            attachments=attach_list or None,
        )

        elapsed_ms = int((time.time() - started) * 1000)
        _json_print(
            {
                "ok": True,
                "stage": "sent",
                "message": "email_sent",
                "elapsed_ms": elapsed_ms,
                "to": to_list,
                "cc": cc_list,
                "bcc": bcc_list,
                "attachments": attach_list,
            }
        )
        return 0

    except Exception as e:
        elapsed_ms = int((time.time() - started) * 1000)
        _json_print(
            {
                "ok": False,
                "stage": "error",
                "error_type": type(e).__name__,
                "error": str(e),
                "elapsed_ms": elapsed_ms,
            }
        )
        return 2


if __name__ == "__main__":
    # 允许 Claude Code/CI 在任意目录调用；不依赖项目内相对路径
    raise SystemExit(main())
