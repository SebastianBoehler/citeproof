"""Optional MCP server wrapper."""

from __future__ import annotations

from citeproof.report import results_to_markdown
from citeproof.verifier import verify_claim_text, verify_draft

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    FastMCP = None
    MCP_IMPORT_ERROR = exc
else:
    MCP_IMPORT_ERROR = None


def create_server():
    """Create the FastMCP server."""

    if FastMCP is None:
        raise RuntimeError('Install MCP support with: uv sync --extra mcp') from MCP_IMPORT_ERROR

    mcp = FastMCP("CiteProof", json_response=True)

    @mcp.tool()
    def verify_claim(claim: str, sources_dir: str, citation_keys: list[str] | None = None) -> dict:
        """Verify whether local sources support a single claim."""

        return verify_claim_text(claim, sources_dir, citation_keys or []).to_dict()

    @mcp.tool()
    def verify_draft_file(draft_path: str, sources_dir: str) -> dict:
        """Verify every citation-bearing claim in a local draft file."""

        results = verify_draft(draft_path, sources_dir)
        return {"results": [result.to_dict() for result in results]}

    @mcp.tool()
    def render_draft_report(draft_path: str, sources_dir: str) -> str:
        """Render a Markdown evidence report for a local draft file."""

        return results_to_markdown(verify_draft(draft_path, sources_dir))

    return mcp


def run() -> None:
    """Run the MCP server over stdio for local agent clients."""

    create_server().run(transport="stdio")
