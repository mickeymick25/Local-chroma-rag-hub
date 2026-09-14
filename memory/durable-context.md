<!-- category: durable_context -->

# Contexte durable

## durable-context::001
<!-- created: 2026-09-04 -->
La stack locale : ChromaDB sur le port 8000, le proxy MCP sur le port 8080,
et l'endpoint Zed sur http://localhost:8080/mcp.

## durable-context::002
<!-- created: 2026-09-04 -->
Le conflit de versions MCP, 1.6.0 contre 1.27.2, est résolu par deux
environnements Python étanches dans le conteneur du proxy.

## durable-context::003
<!-- created: 2026-09-04 -->
Après toute recréation du conteneur proxy, réactiver le serveur chroma dans
les réglages MCP de Zed : l'ancienne session reçoit des erreurs 404.