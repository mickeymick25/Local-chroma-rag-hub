# Les outils Chroma exposés par MCP

## Les outils de gestion des collections

Six outils couvrent le cycle de vie des collections. Lister les collections
avec pagination, pour découvrir l'état de la base. Créer une collection
avec un nom, une fonction d'embedding optionnelle et des métadonnées
libres. Examiner un échantillon de documents pour un aperçu rapide.

Les outils suivants gèrent la durée de vie : les informations détaillées et
le compte de documents d'une collection, la modification du nom ou des
métadonnées, la duplication qui recopie une collection existante, et la
suppression définitive. La suppression est irréversible : elle retire la
collection et tous ses segments du stockage.

## Les outils de gestion des documents

Sept outils couvrent les documents. L'ajout insère des textes avec
identifiants et métadonnées, en calculant les embeddings côté client si la
collection en a une fonction configurée. La requête sémantique cherche par
similarité vectorielle, avec filtrage. La lecture extrait des documents par
identifiants ou par filtres, avec pagination.

La mise à jour modifie le contenu, les métadonnées ou les embeddings
d'identifiants existants. La suppression retire des identifiants précis.
Toutes ces opérations acceptent des listes et travaillent par lots quand
l'implémentation le permet.

## Le filtrage par métadonnées

Les filtres de métadonnées acceptent l'égalité directe par nom de champ, les
comparaisons numériques strictes et larges, et les combinaisons logiques
et ou avec imbrication. Un filtre peut ainsi demander les chunks d'une
catégorie précise dont l'index est inférieur à trois, ou exclure un
fichier source entier.

Ces filtres se combinent avec la recherche sémantique : le serveur
applique d'abord le filtre sur les métadonnées, puis la similarité
vectorielle sur les candidats restants. C'est ce qui permet de restreindre
une recherche à la catégorie des décisions sans perdre la puissance du
vectoriel.

## Le filtrage par contenu

Les filtres de contenu examinent le texte des documents eux-mêmes : la
contenance d'une sous-chaîne, sa négation, les expressions régulières et
leurs négations, avec les mêmes combinaisons logiques. Un filtre peut
ainsi exiger qu'un passage contienne un terme technique tout en excluant
les mentions d'un autre.

Ces filtres sont des filets précieux pour déboguer la base : retrouver
tous les chunks mentionnant un terme donné, vérifier qu'un document a bien
été réindexé, ou préparer la vérité terrain d'un benchmark en localisant
les passages pertinents.