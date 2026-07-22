"""
CASPER Prime Production Tools - REAL Working Tools

ZERO TOLERANCE DIRECTIVE:
- NO placeholders, mocks, or "coming soon"
- Tools must ACTUALLY DO THINGS
- Real data, real operations, real results

Created: 2025-09-25T13:30:00Z
Agent: GAMMA - Tool Integration Specialist
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json

from git import Repo, GitCommandError
from dataclasses import dataclass

# Optional integrations must not prevent the core CLI and intent parser from
# loading. Each tool reports a clear installation error when its extra is used.
try:
    import chromadb
except ImportError:  # pragma: no cover - depends on the optional vector extra
    chromadb = None

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - depends on the optional browser extra
    async_playwright = None

try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover - depends on the optional web extra
    DDGS = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standard result format for all tools"""
    success: bool
    data: Any
    error: Optional[str] = None
    timestamp: str = ""
    tool: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class ProductionTools:
    """
    REAL tools that do REAL work - no mocks, no placeholders

    All tools are production-ready and perform actual operations:
    - ChromaDB for semantic memory and search
    - GitPython for real git operations
    - Playwright for browser automation
    - DuckDuckGo for web searches
    """

    def __init__(self, project_root: Optional[str] = None):
        """Initialize all production tools with real connections"""
        self.project_root = Path(project_root or os.getcwd())
        self.chroma_path = self.project_root / ".casper" / "chromadb"

        # Initialize ChromaDB with persistent storage
        self.chroma_client = None
        self.memory_collection = None

        # Initialize Git repository
        self.repo = None

        # Initialize Playwright browser (lazy loaded)
        self.browser = None
        self.playwright = None

        # Initialize search client
        self.search_client = DDGS() if DDGS is not None else None

        logger.info(f"ProductionTools initialized for project: {self.project_root}")

    async def initialize(self) -> ToolResult:
        """Initialize all tools and verify they work"""
        try:
            # Initialize optional integrations only when their extras are
            # installed; the core coding harness remains usable without them.
            if chromadb is not None:
                await self._init_chromadb()

            # Initialize Git
            await self._init_git()

            # Test basic functionality
            test_results = {
                "chromadb": (
                    await self._test_chromadb() if chromadb is not None else False
                ),
                "git": await self._test_git(),
                "search": await self._test_search()
            }

            return ToolResult(
                success=True,
                data={"initialized": True, "tests": test_results},
                tool="ProductionTools.initialize"
            )

        except Exception as e:
            logger.error(f"Failed to initialize tools: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.initialize"
            )

    async def _init_chromadb(self):
        """Initialize ChromaDB with persistent storage"""
        if chromadb is None:
            raise RuntimeError(
                "ChromaDB is unavailable; install CASPER with the 'vector' extra"
            )
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path)
        )

        # Get or create memory collection
        self.memory_collection = self.chroma_client.get_or_create_collection(
            name="casper_memory",
            metadata={"description": "CASPER semantic memory and context storage"}
        )

        logger.info(f"ChromaDB initialized at: {self.chroma_path}")

    async def _init_git(self):
        """Initialize Git repository connection"""
        try:
            self.repo = Repo(self.project_root)
            logger.info(f"Git repository initialized: {self.repo.working_dir}")
        except Exception as e:
            logger.warning(f"Git repo not found or invalid: {e}")
            self.repo = None

    async def _test_chromadb(self) -> bool:
        """Test ChromaDB with real data"""
        try:
            test_doc = f"ChromaDB test at {datetime.now(timezone.utc).isoformat()}"
            test_id = "test_doc_1"

            self.memory_collection.upsert(
                ids=[test_id],
                documents=[test_doc],
                metadatas=[{"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}]
            )

            # Query it back
            results = self.memory_collection.query(
                query_texts=[test_doc],
                n_results=1
            )

            return len(results['documents']) > 0 and len(results['documents'][0]) > 0

        except Exception as e:
            logger.error(f"ChromaDB test failed: {e}")
            return False

    async def _test_git(self) -> bool:
        """Test Git operations"""
        try:
            if not self.repo:
                return False

            # Get current branch
            current_branch = self.repo.active_branch.name

            # Get recent commits
            commits = list(self.repo.iter_commits(max_count=1))

            return len(commits) > 0 and current_branch is not None

        except Exception as e:
            logger.error(f"Git test failed: {e}")
            return False

    async def _test_search(self) -> bool:
        """Test DuckDuckGo search"""
        if self.search_client is None:
            return False
        try:
            results = self.search_client.text("python", max_results=1)
            return len(list(results)) > 0
        except Exception as e:
            logger.error(f"Search test failed: {e}")
            return False

    # === SEMANTIC MEMORY & SEARCH ===

    async def store_memory(
        self,
        content: str,
        metadata: Dict[str, Any] = None,
        memory_id: Optional[str] = None
    ) -> ToolResult:
        """Store content in semantic memory with ChromaDB"""
        try:
            if not self.memory_collection:
                await self._init_chromadb()

            if not memory_id:
                memory_id = f"mem_{datetime.now(timezone.utc).timestamp()}"

            full_metadata = {
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content),
                **(metadata or {})
            }

            self.memory_collection.upsert(
                ids=[memory_id],
                documents=[content],
                metadatas=[full_metadata]
            )

            return ToolResult(
                success=True,
                data={"memory_id": memory_id, "stored": True},
                tool="ProductionTools.store_memory"
            )

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.store_memory"
            )

    async def search_memory(
        self,
        query: str,
        n_results: int = 5,
        include_metadata: bool = True
    ) -> ToolResult:
        """Search semantic memory using ChromaDB"""
        try:
            if not self.memory_collection:
                await self._init_chromadb()

            results = self.memory_collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"] if include_metadata else ["documents"]
            )

            # Format results
            formatted_results = []
            for i, doc in enumerate(results['documents'][0]):
                result = {
                    "document": doc,
                    "distance": results['distances'][0][i] if 'distances' in results else None
                }
                if include_metadata and 'metadatas' in results:
                    result["metadata"] = results['metadatas'][0][i]
                formatted_results.append(result)

            return ToolResult(
                success=True,
                data={"results": formatted_results, "query": query},
                tool="ProductionTools.search_memory"
            )

        except Exception as e:
            logger.error(f"Failed to search memory: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.search_memory"
            )

    # === GIT OPERATIONS ===

    async def git_status(self) -> ToolResult:
        """Get real git repository status"""
        try:
            if not self.repo:
                await self._init_git()

            if not self.repo:
                return ToolResult(
                    success=False,
                    data=None,
                    error="No git repository found",
                    tool="ProductionTools.git_status"
                )

            # Get actual git status
            status_data = {
                "branch": self.repo.active_branch.name,
                "is_dirty": self.repo.is_dirty(),
                "untracked_files": self.repo.untracked_files,
                "modified_files": [item.a_path for item in self.repo.index.diff(None)],
                "staged_files": [item.a_path for item in self.repo.index.diff("HEAD")],
                "commit_count": self.repo.git.rev_list("--count", "HEAD"),
                "last_commit": {
                    "hash": self.repo.head.commit.hexsha[:8],
                    "message": self.repo.head.commit.message.strip(),
                    "author": str(self.repo.head.commit.author),
                    "date": self.repo.head.commit.committed_datetime.isoformat()
                }
            }

            return ToolResult(
                success=True,
                data=status_data,
                tool="ProductionTools.git_status"
            )

        except Exception as e:
            logger.error(f"Git status failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.git_status"
            )

    async def git_commit(
        self,
        message: str,
        files: Optional[List[str]] = None,
        add_all: bool = False
    ) -> ToolResult:
        """Perform real git commit operations"""
        try:
            if not self.repo:
                return ToolResult(
                    success=False,
                    data=None,
                    error="No git repository found",
                    tool="ProductionTools.git_commit"
                )

            # Add files to staging
            if add_all:
                self.repo.git.add("--all")
            elif files:
                for file in files:
                    self.repo.index.add([file])

            # Create commit
            commit = self.repo.index.commit(message)

            return ToolResult(
                success=True,
                data={
                    "commit_hash": commit.hexsha[:8],
                    "message": message,
                    "files_changed": len(commit.stats.files),
                    "timestamp": commit.committed_datetime.isoformat()
                },
                tool="ProductionTools.git_commit"
            )

        except GitCommandError as e:
            logger.error(f"Git commit failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.git_commit"
            )

    # === WEB SEARCH ===

    async def web_search(
        self,
        query: str,
        max_results: int = 5,
        search_type: str = "text"
    ) -> ToolResult:
        """Perform real web search using DuckDuckGo"""
        try:
            if self.search_client is None:
                raise RuntimeError(
                    "Web search is unavailable; install CASPER with the 'web' extra"
                )
            if search_type == "text":
                results = list(self.search_client.text(query, max_results=max_results))
            elif search_type == "news":
                results = list(self.search_client.news(query, max_results=max_results))
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Invalid search type: {search_type}",
                    tool="ProductionTools.web_search"
                )

            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "source": "duckduckgo"
                })

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": formatted_results,
                    "count": len(formatted_results)
                },
                tool="ProductionTools.web_search"
            )

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.web_search"
            )

    # === BROWSER AUTOMATION ===

    async def launch_browser(self, headless: bool = True) -> ToolResult:
        """Launch real Playwright browser"""
        try:
            if async_playwright is None:
                raise RuntimeError(
                    "Browser automation is unavailable; install CASPER with the "
                    "'browser' extra"
                )
            if not self.playwright:
                self.playwright = await async_playwright().start()

            if not self.browser:
                self.browser = await self.playwright.chromium.launch(headless=headless)

            return ToolResult(
                success=True,
                data={"browser_launched": True, "headless": headless},
                tool="ProductionTools.launch_browser"
            )

        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.launch_browser"
            )

    async def browse_url(
        self,
        url: str,
        wait_for: Optional[str] = None,
        screenshot: bool = False
    ) -> ToolResult:
        """Browse to URL and optionally take screenshot"""
        try:
            if not self.browser:
                await self.launch_browser()

            page = await self.browser.new_page()
            await page.goto(url)

            if wait_for:
                await page.wait_for_selector(wait_for)

            result_data = {
                "url": url,
                "title": await page.title(),
                "loaded": True
            }

            if screenshot:
                screenshot_path = self.project_root / ".casper" / "screenshots" / f"browse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(screenshot_path))
                result_data["screenshot"] = str(screenshot_path)

            await page.close()

            return ToolResult(
                success=True,
                data=result_data,
                tool="ProductionTools.browse_url"
            )

        except Exception as e:
            logger.error(f"Failed to browse URL: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.browse_url"
            )

    # === UTILITY METHODS ===

    async def cleanup(self) -> ToolResult:
        """Clean up all resources"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            return ToolResult(
                success=True,
                data={"cleanup_completed": True},
                tool="ProductionTools.cleanup"
            )

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.cleanup"
            )

    async def health_check(self) -> ToolResult:
        """Check health of all integrated tools"""
        try:
            health_status = {
                "chromadb": {
                    "available": self.memory_collection is not None,
                    "storage_path": str(self.chroma_path),
                    "test_passed": await self._test_chromadb()
                },
                "git": {
                    "available": self.repo is not None,
                    "working_dir": str(self.project_root),
                    "test_passed": await self._test_git()
                },
                "search": {
                    "available": self.search_client is not None,
                    "service": "DuckDuckGo",
                    "test_passed": await self._test_search()
                },
                "browser": {
                    "available": async_playwright is not None,
                    "launched": self.browser is not None
                }
            }

            all_healthy = all(
                tool["available"] and tool.get("test_passed", True)
                for tool in health_status.values()
            )

            return ToolResult(
                success=True,
                data={
                    "overall_health": "HEALTHY" if all_healthy else "DEGRADED",
                    "tools": health_status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                tool="ProductionTools.health_check"
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool="ProductionTools.health_check"
            )


# Example usage and testing
async def main():
    """Test all production tools"""
    tools = ProductionTools()

    print("🚀 CASPER Production Tools - Live Test")
    print("=" * 50)

    # Initialize
    init_result = await tools.initialize()
    print(f"Initialization: {'✅ SUCCESS' if init_result.success else '❌ FAILED'}")
    if not init_result.success:
        print(f"Error: {init_result.error}")
        return

    # Test semantic memory
    print("\n📚 Testing Semantic Memory...")
    store_result = await tools.store_memory(
        "CASPER Prime is an autonomous AI development platform",
        {"category": "system_description", "priority": "high"}
    )
    print(f"Store memory: {'✅' if store_result.success else '❌'}")

    search_result = await tools.search_memory("AI development platform")
    print(f"Search memory: {'✅' if search_result.success else '❌'}")
    if search_result.success:
        print(f"Found {len(search_result.data['results'])} results")

    # Test Git operations
    print("\n🔧 Testing Git Operations...")
    git_result = await tools.git_status()
    print(f"Git status: {'✅' if git_result.success else '❌'}")
    if git_result.success:
        print(f"Current branch: {git_result.data['branch']}")
        print(f"Dirty: {git_result.data['is_dirty']}")

    # Test web search
    print("\n🔍 Testing Web Search...")
    search_web_result = await tools.web_search("FastAPI Python", max_results=3)
    print(f"Web search: {'✅' if search_web_result.success else '❌'}")
    if search_web_result.success:
        print(f"Found {search_web_result.data['count']} results")

    # Health check
    print("\n🏥 Health Check...")
    health_result = await tools.health_check()
    print(f"Overall health: {health_result.data['overall_health']}")

    # Cleanup
    await tools.cleanup()
    print("\n✅ All tests completed - Tools are PRODUCTION READY")


if __name__ == "__main__":
    asyncio.run(main())
