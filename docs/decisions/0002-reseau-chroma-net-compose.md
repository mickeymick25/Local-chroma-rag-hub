# Décision 0002 : le réseau chroma-net est géré par Compose

## Contexte

À l'origine, le conteneur Chroma était attaché au réseau chroma-net par une
commande manuelle de type docker network connect. Ce raccordement hors
déclaratif survivait aux redémarrages mais était silencieusement perdu à
chaque recréation du conteneur : le proxy ne résolvait plus le nom chroma
et la stack entière tombait sans explication visible.

## Décision

Le service chroma déclare explicitement son appartenance au réseau
chroma-net dans le fichier compose. Le réseau reste déclaré external :
Compose gère les attachements mais pas le cycle de vie du réseau, et un
docker compose down ne le supprime jamais.

## Conséquences

La commande complète down puis up est désormais totalement autonome :
aucune action manuelle n'est requise pour reconstruire la stack. La
migration a nécessité une recréation unique du conteneur Chroma, sans
perte de données grâce au volume bind monté sur le répertoire data.

Le DNS interne du réseau est la seule adresse connue des services entre
eux : le nom chroma pour la base, le nom chroma-mcp-proxy pour le MCP.
Aucun service ne dépend d'une adresse IP figée.