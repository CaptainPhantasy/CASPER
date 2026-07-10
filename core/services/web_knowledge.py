"""
WebKnowledge — lets CASPER fetch current documentation it doesn't have memorized.

When the pipeline builds against an unfamiliar or fast-moving API (the MCP
protocol, Apple's Speech / AVFoundation frameworks, SwiftPM manifest format),
the model shouldn't guess from stale training data. This service fetches the
real docs, strips them to text, caches them, and hands condensed excerpts to the
compiler / planner / executor / healer so they build against ground truth.

It is intentionally dependency-free (urllib + regex) so it works anywhere the
backend runs. Fetches are cached on disk to avoid re-downloading.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_UA = "CASPER-Prime/1.0 (+https://github.com/CaptainPhantasy/CASPER)"

# Curated, high-signal documentation sources keyed by topic. The pipeline matches
# a task's keywords against these to decide what to fetch. Extend freely.
KNOWLEDGE_SOURCES: Dict[str, List[str]] = {
    "mcp": [
        "https://modelcontextprotocol.io/llms-full.txt",
        "https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/README.md",
    ],
    "mcp-swift": [
        "https://raw.githubusercontent.com/modelcontextprotocol/swift-sdk/main/README.md",
    ],
    "speech": [
        "https://developer.apple.com/documentation/speech",
    ],
    "tts": [
        "https://developer.apple.com/documentation/avfoundation/avspeechsynthesizer",
    ],
    "stt": [
        "https://developer.apple.com/documentation/speech/sfspeechrecognizer",
    ],
    "swiftpm": [
        "https://raw.githubusercontent.com/swiftlang/swift-package-manager/main/Documentation/PackageDescription.md",
    ],
    "menubar": [
        "https://developer.apple.com/documentation/appkit/nsstatusitem",
    ],
}

# Keyword → topic routing so a natural task description picks the right docs.
_TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "mcp": ["mcp", "model context protocol", "json-rpc", "tool server"],
    "mcp-swift": ["mcp", "swift sdk"],
    "speech": ["speech", "voice", "recogni"],
    "tts": ["tts", "text to speech", "speak", "avspeech", "synthe"],
    "stt": ["stt", "speech to text", "transcrib", "listen", "dictation", "sfspeech"],
    "swiftpm": ["package.swift", "swiftpm", "swift package"],
    "menubar": ["menu bar", "menubar", "status bar", "nsstatusitem", "top bar"],
}


class WebKnowledge:
    def __init__(self, project_root: str, ttl_seconds: int = 7 * 24 * 3600):
        self.cache_dir = Path(project_root) / ".casper" / "knowledge_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds

    # --- fetch -----------------------------------------------------------
    def fetch(self, url: str, max_chars: int = 8000, force: bool = False) -> str:
        """Fetch a URL, strip to text, cache. Returns "" on failure (never raises)."""
        key = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_file = self.cache_dir / f"{key}.txt"
        if not force and cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < self.ttl:
            return cache_file.read_text(encoding="utf-8", errors="replace")[:max_chars]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/html,text/plain,*/*"})
            with urllib.request.urlopen(req, timeout=12) as r:
                raw = r.read(1_500_000)
                ctype = r.headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="replace")
            if "html" in ctype or text.lstrip().lower().startswith("<!doctype") or "<html" in text[:200].lower():
                text = self._html_to_text(text)
            text = self._collapse(text)
            try:
                cache_file.write_text(text, encoding="utf-8")
            except Exception:
                pass
            return text[:max_chars]
        except Exception as e:
            logger.warning(f"WebKnowledge fetch failed for {url}: {e}")
            return ""

    # --- research --------------------------------------------------------
    def topics_for(self, query: str) -> List[str]:
        q = query.lower()
        topics = []
        for topic, kws in _TOPIC_KEYWORDS.items():
            if any(kw in q for kw in kws):
                topics.append(topic)
        return topics

    def research(self, query: str, max_sources: int = 4, chars_per_source: int = 4000) -> Dict[str, str]:
        """Return {url: excerpt} of docs relevant to the query."""
        urls: List[str] = []
        for topic in self.topics_for(query):
            for u in KNOWLEDGE_SOURCES.get(topic, []):
                if u not in urls:
                    urls.append(u)
        out: Dict[str, str] = {}
        for u in urls[:max_sources]:
            text = self.fetch(u, max_chars=chars_per_source)
            if text.strip():
                out[u] = text
        return out

    def research_brief(self, query: str, max_chars: int = 9000) -> str:
        """A single text block of relevant docs, ready to drop into a prompt."""
        docs = self.research(query)
        if not docs:
            return ""
        parts = [f"### Reference: {u}\n{txt}" for u, txt in docs.items()]
        brief = "\n\n".join(parts)
        return brief[:max_chars]

    # --- helpers ---------------------------------------------------------
    @staticmethod
    def _html_to_text(html: str) -> str:
        html = re.sub(r"(?is)<(script|style|noscript|svg|head).*?</\1>", " ", html)
        html = re.sub(r"(?s)<!--.*?-->", " ", html)
        html = re.sub(r"(?i)<br\s*/?>", "\n", html)
        html = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section)>", "\n", html)
        html = re.sub(r"<[^>]+>", " ", html)
        html = (html.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
        return html

    @staticmethod
    def _collapse(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return text.strip()


class GitHubKnowledge:
    """
    Lets CASPER use GitHub as a live knowledge base: read READMEs, browse a
    repository's file tree, fetch specific source files, and search code across
    GitHub. This is how the platform finds real, working examples and current
    SDK usage when building an unfamiliar kind of application.

    Uses the public GitHub REST API (api.github.com) + raw.githubusercontent.com.
    Honors GITHUB_TOKEN if set (higher rate limits + private repos), but works
    unauthenticated for public repos.
    """

    API = "https://api.github.com"
    RAW = "https://raw.githubusercontent.com"

    def __init__(self, project_root: str, ttl_seconds: int = 3 * 24 * 3600):
        self.cache_dir = Path(project_root) / ".casper" / "knowledge_cache" / "github"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def _headers(self) -> Dict[str, str]:
        h = {"User-Agent": _UA, "Accept": "application/vnd.github+json",
             "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, url: str, accept_json: bool = True, max_bytes: int = 1_500_000) -> Optional[Any]:
        key = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < self.ttl:
            raw = cache_file.read_text(encoding="utf-8", errors="replace")
            return json.loads(raw) if accept_json else raw
        try:
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read(max_bytes).decode("utf-8", errors="replace")
            try:
                cache_file.write_text(data, encoding="utf-8")
            except Exception:
                pass
            return json.loads(data) if accept_json else data
        except Exception as e:
            logger.warning(f"GitHub fetch failed {url}: {e}")
            return None

    # --- public API ------------------------------------------------------
    def get_readme(self, repo: str, ref: str = "HEAD", max_chars: int = 14000) -> str:
        """repo = 'owner/name'. Returns README text."""
        meta = self._get(f"{self.API}/repos/{repo}/readme?ref={ref}")
        if isinstance(meta, dict) and meta.get("download_url"):
            txt = self._get(meta["download_url"], accept_json=False)
            return (txt or "")[:max_chars]
        return ""

    def list_tree(self, repo: str, ref: str = "HEAD", max_entries: int = 400) -> List[str]:
        """Return repo file paths (recursive)."""
        # Resolve ref to a tree sha via the branches/commits API when needed.
        data = self._get(f"{self.API}/repos/{repo}/git/trees/{ref}?recursive=1")
        if not isinstance(data, dict):
            return []
        return [e["path"] for e in data.get("tree", []) if e.get("type") == "blob"][:max_entries]

    def get_file(self, repo: str, path: str, ref: str = "HEAD", max_chars: int = 12000) -> str:
        """Fetch a single file's contents via raw.githubusercontent.com."""
        url = f"{self.RAW}/{repo}/{ref}/{path}"
        txt = self._get(url, accept_json=False)
        return (txt or "")[:max_chars]

    def search_code(self, query: str, repo: Optional[str] = None, limit: int = 5) -> List[Dict[str, str]]:
        """Search code on GitHub. Returns [{repo, path, url}]. Needs network; best with GITHUB_TOKEN."""
        q = query + (f" repo:{repo}" if repo else "")
        url = f"{self.API}/search/code?q={urllib.parse.quote(q)}&per_page={limit}"
        data = self._get(url)
        out: List[Dict[str, str]] = []
        if isinstance(data, dict):
            for item in data.get("items", [])[:limit]:
                out.append({
                    "repo": item.get("repository", {}).get("full_name", ""),
                    "path": item.get("path", ""),
                    "url": item.get("html_url", ""),
                })
        return out

    def find_examples(self, repo: str, name_filters: List[str], ref: str = "HEAD",
                      max_files: int = 3, chars_per_file: int = 4000) -> Dict[str, str]:
        """Browse a repo's tree and return contents of files whose path matches any filter."""
        tree = self.list_tree(repo, ref)
        picked = [p for p in tree if any(f.lower() in p.lower() for f in name_filters)]
        out: Dict[str, str] = {}
        for p in picked[:max_files]:
            content = self.get_file(repo, p, ref, max_chars=chars_per_file)
            if content.strip():
                out[f"{repo}/{p}"] = content
        return out
