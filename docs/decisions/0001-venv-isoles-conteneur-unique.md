# Décision 0001 : deux venv Python isolés dans un conteneur unique

## Contexte

Le proxy MCP en version 0.12.0 exige un SDK MCP supérieur à 1.17, tandis
que le serveur chroma-mcp 0.2.6 impose un pin strict sur MCP 1.6.0. Les
deux outils ne peuvent donc pas cohabiter dans un même environnement
Python : toute installation unifiée casse l'un des deux programmes.

## Décision

Le conteneur chroma-mcp-proxy embarque deux environnements étanches :
l'environnement système porte mcp-proxy et MCP 1.27.2, tandis qu'un venv
dédié sous opt/chroma-mcp porte chroma-mcp et MCP 1.6.0. Un script wrapper
dans usr/local/bin pointe vers le binaire du venv pour que le proxy lance
toujours le bon interpréteur.

## Alternatives rejetées

Downgrader mcp-proxy vers une version compatible MCP 1.6.0 a été écarté :
c'est une maintenance fragile qui contourne le problème plutôt qu'elle ne
le résout. Séparer en deux conteneurs a aussi été écarté : la complexité
réseau et de supervision ajoutée n'apporte aucun gain, la frontière stdio
étant de toute façon locale au conteneur.

## Conséquences

La frontière entre les deux mondes est le protocole stdio avec du JSON-RPC
ligne à ligne, jamais l'API Python. Les versions des SDK peuvent donc
diverger librement de part et d'autre. La validation s'automatise en une
commande docker run par interpréteur, qui affiche la version du paquet mcp
attendue dans chaque environnement.