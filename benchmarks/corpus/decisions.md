# Les décisions d'architecture de la stack

## Décision 0001 : deux environnements Python isolés

Le conflit de versions du SDK MCP ne pouvait pas être résolu par une
simple mise à jour : le proxy exige une version récente, le serveur Chroma
en exige une ancienne verrouillée. Downgrader le proxy vers une version
compatible avec l'ancien SDK a été écarté : c'est une maintenance fragile
qui contourne le problème plutôt qu'elle ne le résout, et qui lie le
projet à une version obsolète.

Séparer les deux programmes en deux conteneurs a également été écarté : la
frontière stdio est de toute façon locale au conteneur, et la séparation
ajoutait de la supervision sans aucun gain de sûreté. La décision finale,
deux environnements Python dans un seul conteneur, combine l'isolation
réelle des dépendances et la simplicité d'un unique cycle de vie.

## Décision 0002 : le réseau géré par le compose

À l'origine, le conteneur de base était raccordé au réseau interne par une
commande manuelle exécutée une fois. Ce raccordement survivait aux
redémarrages mais était silencieusement perdu à chaque recréation du
conteneur : le proxy ne résolvait plus le nom de la base et la stack
entière tombait sans explication.

La décision a été de déclarer le raccordement dans le fichier compose, au
prix d'une recréation unique du conteneur, sans perte de données grâce au
volume monté. Depuis, un arrêt et un redémarrage complets de la stack ne
dépendent plus d'aucune commande manuelle : le réseau se reconstruit de
lui-même.

Le réseau reste déclaré external : Compose gère les attachements mais
jamais la suppression du réseau, ce qui évite les accidents en cascade
lors d'un compose down.

## Décision 0003 : le modèle d'embedding provisoire

Le modèle d'embedding initial a été choisi pour trois critères
opérationnels : une qualité multilingue élevée pour le français, des
vecteurs de mille vingt-quatre dimensions, et surtout l'absence de
préfixes obligatoires. Cette absence garantit que l'indexation et les
requêtes produisent des vecteurs comparables sans logique de préfixe à
maintenir des deux côtés.

La décision est explicitement provisoire : un benchmark de rappel
mesurera objectivement les candidats sur un corpus de référence avant
tout gel du choix. Les alternatives notables exigent des préfixes
distincts pour les documents et pour les requêtes, une contrainte
d'intégration qui pèse dans la balance autant que la qualité brute des
vecteurs.