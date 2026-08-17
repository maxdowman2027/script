#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 GDVS GitLab 三个仓库的 ``4.0.0/4.0.0`` 目录中，按 pipeline_id 匹配条目并下载 tar。

默认仓库（可用 ``--repos`` 覆盖）::
  chip11.2.1_mp/wifi-fpga
  chip11.2.1_mp/wifimac-csv
  chip11.2.1_mp/wifibb-csv

匹配规则（满足任一即可）::
  1) 子目录/文件名以 ``pipeline_id`` 结尾
  2) 该路径 Last commit 的 title/message 以 ``pipeline_id`` 结尾
     （对应网页 Tree 视图中 “Last commit” 列）

下载等价于网页 “Download this directory” → tar::
  GET /api/v4/projects/:id/repository/archive.tar?sha=<ref>&path=<subdir>

认证（任选其一）::
  - ``--token`` / 环境变量 ``GDVS_TOKEN`` / ``GITLAB_PRIVATE_TOKEN``
    （GitLab Settings → Access Tokens，需 ``read_api`` + ``read_repository``）
  - ``--cookie``：浏览器登录后的 Cookie 字符串（备选）

示例::
  set GDVS_TOKEN=glpat-xxxx
  python download_gdvs_pipeline_dirs.py --pipeline-id 12345 -o D:\\download\\gdvs
  python download_gdvs_pipeline_dirs.py -p 12345 -o .\\out --format tar.gz --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_BASE_URL = "https://gdvs.espressif.cn:7788"
DEFAULT_REF = "master"
DEFAULT_TREE_PATH = "4.0.0/4.0.0"
DEFAULT_REPOS = (
    "chip11.2.1_mp/wifi-fpga",
    "chip11.2.1_mp/wifimac-csv",
    "chip11.2.1_mp/wifibb-csv",
)
DEFAULT_FORMAT = "tar"  # GitLab archive.tar（对应 UI tar）


def _ssl_context(insecure: bool) -> ssl.SSLContext:
    if insecure:
        return ssl._create_unverified_context()
    return ssl.create_default_context()


class GdvsClient:
    def __init__(
        self,
        base_url: str,
        *,
        token: Optional[str] = None,
        cookie: Optional[str] = None,
        insecure: bool = False,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = (token or "").strip() or None
        self.cookie = (cookie or "").strip() or None
        self.timeout = float(timeout)
        self.ctx = _ssl_context(insecure)
        if not self.token and not self.cookie:
            raise ValueError(
                "需要认证：请设置 --token / 环境变量 GDVS_TOKEN|"
                "GITLAB_PRIVATE_TOKEN，或传入 --cookie"
            )

    def _headers(self) -> Dict[str, str]:
        h = {
            "User-Agent": "download_gdvs_pipeline_dirs/1.0",
            "Accept": "application/json, application/octet-stream, */*",
        }
        if self.token:
            h["PRIVATE-TOKEN"] = self.token
        if self.cookie:
            h["Cookie"] = self.cookie
        return h

    def request(
        self,
        url: str,
        *,
        binary: bool = False,
    ) -> Tuple[Any, Dict[str, str]]:
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(
                req, timeout=self.timeout, context=self.ctx
            ) as resp:
                raw = resp.read()
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace") if e.fp else ""
            raise RuntimeError(
                f"HTTP {e.code} {e.reason} for {url}\n{body[:500]}"
            ) from e
        if binary:
            return raw, hdrs
        text = raw.decode("utf-8", "replace")
        if not text.strip():
            return None, hdrs
        try:
            return json.loads(text), hdrs
        except json.JSONDecodeError:
            return text, hdrs

    def api_url(self, path: str, query: Optional[Dict[str, Any]] = None) -> str:
        path = path if path.startswith("/") else "/" + path
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(
                {k: v for k, v in query.items() if v is not None}
            )
        return url

    @staticmethod
    def project_id(project_path: str) -> str:
        return urllib.parse.quote(project_path.strip("/"), safe="")

    def list_tree(
        self,
        project_path: str,
        tree_path: str,
        ref: str,
    ) -> List[Dict[str, Any]]:
        """Paginated repository tree listing."""
        proj = self.project_id(project_path)
        page = 1
        out: List[Dict[str, Any]] = []
        while True:
            url = self.api_url(
                f"/api/v4/projects/{proj}/repository/tree",
                {
                    "path": tree_path,
                    "ref": ref,
                    "per_page": 100,
                    "page": page,
                },
            )
            data, _ = self.request(url)
            if not isinstance(data, list):
                raise RuntimeError(
                    f"unexpected tree response for {project_path}: {type(data)}"
                )
            if not data:
                break
            out.extend(data)
            if len(data) < 100:
                break
            page += 1
        return out

    def last_commit_for_path(
        self,
        project_path: str,
        entry_path: str,
        ref: str,
    ) -> Optional[Dict[str, Any]]:
        """Newest commit touching ``entry_path`` on ``ref``."""
        proj = self.project_id(project_path)
        url = self.api_url(
            f"/api/v4/projects/{proj}/repository/commits",
            {
                "ref_name": ref,
                "path": entry_path,
                "per_page": 1,
            },
        )
        data, _ = self.request(url)
        if isinstance(data, list) and data:
            return data[0]
        return None

    def download_archive(
        self,
        project_path: str,
        *,
        sha: str,
        subpath: str,
        fmt: str = "tar",
    ) -> Tuple[bytes, str]:
        """
        Download directory archive (UI: Download this directory).

        Returns (content_bytes, suggested_filename).
        """
        proj = self.project_id(project_path)
        fmt = (fmt or "tar").lstrip(".")
        url = self.api_url(
            f"/api/v4/projects/{proj}/repository/archive.{fmt}",
            {"sha": sha, "path": subpath},
        )
        raw, hdrs = self.request(url, binary=True)
        name = _filename_from_headers(hdrs) or _default_archive_name(
            project_path, sha, subpath, fmt
        )
        return raw, name


def _filename_from_headers(hdrs: Dict[str, str]) -> Optional[str]:
    cd = hdrs.get("content-disposition") or ""
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd, re.I)
    if m:
        return urllib.parse.unquote(m.group(1).strip())
    return None


def _default_archive_name(
    project_path: str, sha: str, subpath: str, fmt: str
) -> str:
    repo = project_path.rstrip("/").split("/")[-1]
    leaf = subpath.rstrip("/").split("/")[-1] or "root"
    safe_sha = re.sub(r"[^\w.-]+", "_", sha)[:12]
    return f"{repo}-{leaf}-{safe_sha}.{fmt}"


def _ends_with_pipeline_id(text: str, pipeline_id: str) -> bool:
    s = (text or "").strip()
    pid = (pipeline_id or "").strip()
    if not s or not pid:
        return False
    # allow optional punctuation after id at end of commit title
    if s.endswith(pid):
        return True
    return bool(re.search(rf"(?:^|[\s_\-/]){re.escape(pid)}\s*$", s))


def find_matches(
    client: GdvsClient,
    project_path: str,
    *,
    tree_path: str,
    ref: str,
    pipeline_id: str,
    match_name: bool = True,
    match_commit: bool = True,
) -> List[Dict[str, Any]]:
    """
    Return matched tree entries with last-commit info.

    Each item: {name, path, type, match_reason, commit_title, commit_id}
    """
    entries = client.list_tree(project_path, tree_path, ref)
    matches: List[Dict[str, Any]] = []
    for ent in entries:
        name = str(ent.get("name") or "")
        path = str(ent.get("path") or "")
        etype = str(ent.get("type") or "")
        reasons: List[str] = []
        commit = None
        title = ""

        if match_name and _ends_with_pipeline_id(name, pipeline_id):
            reasons.append("name")

        if match_commit:
            commit = client.last_commit_for_path(project_path, path, ref)
            if commit:
                title = str(
                    commit.get("title")
                    or commit.get("message")
                    or ""
                ).split("\n", 1)[0]
                if _ends_with_pipeline_id(title, pipeline_id):
                    reasons.append("last_commit")

        if not reasons:
            continue

        matches.append(
            {
                "name": name,
                "path": path,
                "type": etype,
                "match_reason": "+".join(reasons),
                "commit_title": title,
                "commit_id": (commit or {}).get("id") if commit else None,
                "web_url": (
                    f"{client.base_url}/{project_path}/-/tree/{ref}/{path}"
                ),
            }
        )
    return matches


def save_bytes(data: bytes, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def parse_repos(text: Optional[str]) -> List[str]:
    if not text:
        return list(DEFAULT_REPOS)
    parts = re.split(r"[,;\s]+", text.strip())
    return [p for p in parts if p]


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "按 pipeline_id 在 GDVS wifi-fpga / wifimac-csv / wifibb-csv "
            "的 4.0.0/4.0.0 下匹配 Last commit/目录名，并下载目录 tar"
        )
    )
    p.add_argument(
        "-p",
        "--pipeline-id",
        required=True,
        help="流水线 ID；匹配 Last commit 文案或目录名末尾",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        required=True,
        type=Path,
        help="本地下载目录",
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("GDVS_BASE_URL", DEFAULT_BASE_URL),
        help=f"GitLab 根地址（默认 {DEFAULT_BASE_URL}）",
    )
    p.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help=f"分支/标签（默认 {DEFAULT_REF}）",
    )
    p.add_argument(
        "--tree-path",
        default=DEFAULT_TREE_PATH,
        help=f"浏览根路径（默认 {DEFAULT_TREE_PATH}）",
    )
    p.add_argument(
        "--repos",
        default=None,
        help="仓库路径列表，逗号分隔（默认三个 chip11.2.1_mp/* 仓库）",
    )
    p.add_argument(
        "--format",
        dest="archive_format",
        default=DEFAULT_FORMAT,
        choices=("tar", "tar.gz", "zip", "tar.bz2"),
        help="归档格式（默认 tar，对应 UI Download this directory → tar）",
    )
    p.add_argument(
        "--token",
        default=None,
        help="GitLab Private Token（也可用环境变量 GDVS_TOKEN / GITLAB_PRIVATE_TOKEN）",
    )
    p.add_argument(
        "--cookie",
        default=None,
        help="可选：浏览器 Cookie 字符串（无 token 时使用）",
    )
    p.add_argument(
        "--match-name-only",
        action="store_true",
        help="仅按目录/文件名末尾匹配，不查询 Last commit（更快）",
    )
    p.add_argument(
        "--match-commit-only",
        action="store_true",
        help="仅按 Last commit 文案末尾匹配",
    )
    p.add_argument(
        "--insecure",
        action="store_true",
        help="跳过 TLS 证书校验（内网自签证书时可用）",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="只列出匹配项，不下载",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    token = (
        args.token
        or os.environ.get("GDVS_TOKEN")
        or os.environ.get("GITLAB_PRIVATE_TOKEN")
    )
    cookie = args.cookie or os.environ.get("GDVS_COOKIE")
    pipeline_id = str(args.pipeline_id).strip()
    out_dir: Path = args.output_dir
    repos = parse_repos(args.repos)

    match_name = not args.match_commit_only
    match_commit = not args.match_name_only
    if args.match_name_only and args.match_commit_only:
        print("[ERROR] --match-name-only 与 --match-commit-only 不能同时使用", file=sys.stderr)
        return 2

    try:
        client = GdvsClient(
            args.base_url,
            token=token,
            cookie=cookie,
            insecure=args.insecure,
        )
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    print(f"[INFO] base={args.base_url}")
    print(f"[INFO] pipeline_id={pipeline_id}")
    print(f"[INFO] tree={args.ref}:{args.tree_path}")
    print(f"[INFO] output={out_dir.resolve()}")
    print(f"[INFO] repos={repos}")

    total_ok = 0
    total_fail = 0
    all_matches: List[Tuple[str, Dict[str, Any]]] = []

    for repo in repos:
        print(f"\n==== {repo} ====")
        try:
            matches = find_matches(
                client,
                repo,
                tree_path=args.tree_path,
                ref=args.ref,
                pipeline_id=pipeline_id,
                match_name=match_name,
                match_commit=match_commit,
            )
        except Exception as e:
            print(f"[ERROR] 列出/匹配失败: {e}", file=sys.stderr)
            total_fail += 1
            continue

        if not matches:
            print(f"[WARN] 未找到匹配 pipeline_id={pipeline_id} 的条目")
            continue

        for m in matches:
            print(
                f"[MATCH] {m['path']}  ({m['match_reason']})  "
                f"commit={m.get('commit_title')!r}"
            )
            print(f"        {m['web_url']}")
            all_matches.append((repo, m))

            if args.dry_run:
                continue

            subpath = m["path"]
            # Prefer commit id when available so archive matches that revision;
            # otherwise use branch tip (same as browsing master tree).
            sha = m.get("commit_id") or args.ref
            try:
                data, fname = client.download_archive(
                    repo,
                    sha=str(sha),
                    subpath=subpath,
                    fmt=args.archive_format,
                )
            except Exception as e:
                print(f"[ERROR] 下载失败 {subpath}: {e}", file=sys.stderr)
                total_fail += 1
                continue

            # save under <out>/<repo_leaf>/
            repo_leaf = repo.rstrip("/").split("/")[-1]
            dest = out_dir / repo_leaf / fname
            # avoid overwrite
            if dest.exists():
                stem, suf = dest.name, ""
                # keep compound suffixes like .tar.gz
                for ext in (".tar.gz", ".tar.bz2", ".tar", ".zip"):
                    if dest.name.endswith(ext):
                        stem = dest.name[: -len(ext)]
                        suf = ext
                        break
                n = 1
                while dest.exists():
                    dest = dest.with_name(f"{stem}_{n}{suf}")
                    n += 1
            save_bytes(data, dest)
            print(f"[OK] saved {dest}  ({len(data)} bytes)")
            total_ok += 1

    print(
        f"\n[INFO] done: matches={len(all_matches)}  "
        f"downloaded={total_ok}  failed={total_fail}"
    )
    if not all_matches:
        return 1
    if total_fail and not args.dry_run:
        return 1
    return 0


if __name__ == "__main__":
    # Python 3.7 compat: annotations future may need typing.List already imported
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[INFO] interrupted", file=sys.stderr)
        raise SystemExit(130)
