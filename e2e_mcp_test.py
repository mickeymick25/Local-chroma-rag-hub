"""Test MCP bout-en-bout (deux transports).

Chaine validee :
    client MCP (ce script, mcp 1.27.2, conteneur temporaire sur chroma-net)
      -> mcp-proxy :8080
           /sse : transport SSE        (GET /sse + POST /messages/)
           /mcp : transport Streamable HTTP (POST) — celui utilise par Zed
      -> stdio -> chroma-mcp (mcp 1.6.0)
      -> HTTP  -> chroma :8000
      -> chroma.sqlite3

Suites executees par transport :
    initialize, tools/list, get_collection_info, requete semantique.

S'exécute dans un conteneur temporaire sur chroma-net :

    docker run --rm --network chroma-net \
      -v "$PWD/e2e_mcp_test.py:/tmp/e2e.py:ro" \
      --entrypoint python local/chroma-mcp-proxy:latest /tmp/e2e.py
"""

import anyio
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

BASE_URL = "http://chroma-mcp-proxy:8080"
QUERY = "comment la stack survit-elle à un redémarrage complet de la machine ?"


async def run_suite(session, label) -> None:
    result = await session.initialize()
    print(f"[{label}] INITIALIZE protocol={result.protocolVersion} "
          f"server={result.serverInfo.name}")

    tools = await session.list_tools()
    print(f"[{label}] TOOLS/LIST  {len(tools.tools)} outils exposes")

    info = await session.call_tool("chroma_get_collection_info",
                                   {"collection_name": "project_knowledge"})
    print(f"[{label}] GET_COLLECTION_INFO isError={info.isError}")
    for content in info.content:
        print("    ", getattr(content, "text", "")[:500])

    res = await session.call_tool("chroma_query_documents", {
        "collection_name": "project_knowledge",
        "query_texts": [QUERY],
        "n_results": 3,
        "include": ["documents", "metadatas", "distances"],
    })
    print(f"[{label}] QUERY isError={res.isError}")
    print(f"[{label}] Requete : {QUERY}")
    for content in res.content:
        print("    ", getattr(content, "text", "")[:800])


async def main() -> None:
    # Transport SSE
    async with sse_client(f"{BASE_URL}/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await run_suite(session, "SSE /sse")

    # Transport Streamable HTTP (utilise par Zed)
    async with streamablehttp_client(f"{BASE_URL}/mcp") as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await run_suite(session, "STREAMABLE-HTTP /mcp")


if __name__ == "__main__":
    anyio.run(main)