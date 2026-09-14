# Persistance et stockage dans la stack

## Ce qui est persisté

Les données de la base vivent dans une base SQLite et ses segments,
stockés dans le répertoire data monté depuis la machine hôte. Chaque
collection, chaque document, chaque vecteur et chaque métadonnée s'y
trouvent. C'est l'unique source de vérité de la mémoire vectorielle, à
l'exception des documents sources qui vivent dans Git.

Le répertoire data est monté dans le conteneur de base par un bind mount :
les écritures de la base aboutissent directement sur le disque de l'hôte.
Ce choix rend le conteneur jetable et les données immortelles, au sens où
elles survivent à toutes les opérations de cycle de vie des conteneurs.

Recréer le conteneur de base, par exemple pour changer son image ou sa
configuration réseau, ne perd aucune donnée : le nouveau conteneur
retrouve le répertoire tel qu'il a été laissé. C'est le mécanisme qui a
rendu indolore la migration du raccordement réseau vers le mode
déclaratif.

## Ce qui est éphémère

Tout ce qui n'est pas monté en volume est reconstruit à chaque recréation
de conteneur. Le cas le plus notable est le cache du modèle d'embedding
par défaut de Chroma, posé dans le répertoire caché de l'utilisateur root
du conteneur proxy : après une recréation, le premier calcul d'embedding
doit retélécharger le modèle, et le premier appel peut dépasser le délai
d'attente du client MCP.

La session MCP du proxy subit le même sort : les sessions vivent en
mémoire du processus, une recréation les efface, et le client doit se
réinitialiser. Ces deux coûts de redémarrage sont connus et documentés
dans le runbook.

## Sauvegarder la base

Sauvegarder la mémoire vectorielle revient à copier le répertoire data de
l'hôte : la base SQLite et les segments forment un ensemble cohérent.
Comme la base n'est qu'un cache dérivé du dépôt Git et de l'indexeur, une
sauvegarde est une commodité de restauration rapide, pas une nécessité
absolue : une réindexation complète reconstruit la même collection à
partir des sources.

Cette philosophie sépare nettement les rôles : Git garde les documents
originaux, la base garde les vecteurs dérivés. Toute question de cohérence
se résout par une réindexation, jamais par une réparation manuelle de la
base.