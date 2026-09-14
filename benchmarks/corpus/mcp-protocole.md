# Le protocole Model Context Protocol dans la stack

## Rôle du protocole

Le protocole Model Context Protocol, ou MCP, standardise l'échange entre
les applications de langage et les sources d'outils et de données. Dans
cette stack, il permet à l'agent de Zed de découvrir et d'appeler les
outils Chroma comme n'importe quel outil intégré : lister les collections,
créer, ajouter, interroger, mettre à jour, supprimer.

La découverte est dynamique : le client interroge le serveur pour obtenir
la liste des outils, leurs descriptions et leurs signatures. Toute évolution
du serveur Chroma, comme l'ajout d'un outil, est visible par l'agent sans
configuration supplémentaire.

## Les deux transports du proxy

Le proxy expose simultanément deux transports HTTP. Le transport SSE,
historique, se branche par un GET sur le chemin sse puis envoie ses
messages par des POST vers un point d'entrée de session dédié. Le
transport Streamable HTTP, plus récent, échange tout par des POST directs
sur le chemin mcp.

Les deux transports ont été validés de bout en bout : initialisation du
protocole, découverte des outils, appel réel à un outil. Ils servent des
besoins différents : le SSE convient aux clients qui gèrent un flux longue
durée, le Streamable HTTP aux clients modernes qui préfèrent des
échanges requête-réponse.

## Pourquoi Zed utilise le chemin mcp

L'agent de Zed parle Streamable HTTP : il émet des POST directement sur
l'URL configurée. Configurer Zed sur le chemin sse produit une erreur 405,
car ce chemin n'accepte que le GET du flux d'événements. Le chemin mcp est
donc le seul endpoint valide pour Zed dans cette stack.

Ce point a été validé empiriquement : les journaux du proxy montrent les
tentatives POST sur le chemin sse rejetées, puis le succès complet sur le
chemin mcp, avec découverte des treize outils et appels fonctionnels.

## Les sessions et leur fragilité

Le transport Streamable HTTP attribue un identifiant de session au client
lors de l'initialisation. Les requêtes suivantes portent cet identifiant
dans un en-tête dédié, et le serveur route les messages vers la session
correspondante.

Cette mémoire a une contrepartie : les sessions vivent en mémoire dans le
processus du proxy. Recréer le conteneur du proxy efface toutes les
sessions, et le client garde un identifiant devenu invalide : ses requêtes
reçoivent un code 404 jusqu'à ce qu'il se réinitialise.

Avec Zed, la récupération se fait en désactivant puis réactivant le serveur
dans les réglages MCP de l'éditeur, ou en redémarrant l'éditeur. Ce
comportement est documenté dans le runbook car il se reproduit à chaque
recréation du conteneur proxy.

## Le nombre et la nature des outils

Le serveur chroma-mcp expose treize outils couvrant la gestion des
collections et celle des documents : lister, créer, examiner, modifier,
dupliquer et supprimer des collections, ajouter, interroger, lire, mettre
à jour et supprimer des documents.

Les requêtes sémantiques acceptent des filtres de métadonnées et de
contenu : égalité, comparaisons, combinaisons logiques, expressions
régulières. Cette richesse permet à l'agent de combiner recherche
vectorielle et contraintes précises, par exemple restreindre une recherche
à une catégorie de documents.