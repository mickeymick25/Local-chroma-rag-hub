# Le service Ollama dans la stack

## Positionnement du service

Ollama n'est pas conteneurisé dans cette stack : le service tourne en
nativif sur la machine hôte, en application du système. Ce choix découle du
fait qu'il sert à la fois les modèles de langage utilisés par Zed et le
modèle d'embedding utilisé par l'indexeur, et qu'il doit rester disponible
pour tous les clients, conteneurisés ou non.

Depuis les conteneurs, le service est joint par l'adresse spéciale
host.docker.internal sur le port 11434. Cette adresse résout la machine
hôte depuis l'intérieur d'un conteneur Docker Desktop, sans exiger de
configuration réseau particulière. Elle est utilisée à deux endroits : par
l'indexeur pour les embeddings des documents, et par la fonction
d'embedding des requêtes dans le venv de chroma-mcp.

## La séparation des modèles

Ollama héberge deux familles de modèles aux rôles distincts. Les modèles
de langage servent la conversation de l'agent : ce sont des modèles
distantes de type cloud, invoqués par l'éditeur via son fournisseur
Ollama. Le modèle d'embedding, lui, est un modèle local installé sur la
machine, qui ne quitte jamais le disque.

Cette séparation est la clé du découplage : le choix du modèle de langage
n'affecte ni la base, ni l'indexeur, ni les vecteurs. Le modèle d'embedding
est le seul à toucher la base, et tout changement de ce côté impose une
réindexation complète.

## Le modèle d'embedding en place

Le modèle retenu pour la preuve de concept est un modèle multilingue
réputé pour sa qualité en français, produisant des vecteurs de mille
vingt-quatre dimensions. Son intégration ne demande aucun préfixe : le
même texte est encodé de la même façon côté documents et côté requêtes,
ce qui élimine une classe entière de bogues de cohérence.

Les alternatives notables, comme le modèle nomic, exigent des préfixes
différents pour les documents et pour les requêtes. Cette contrainte
d'intégration est prise en compte dans le futur benchmark : les candidats
seront évalués selon le pipeline réellement utilisable, préfixes inclus,
et non selon les seuls vecteurs dans des conditions artificielles.

## L'API d'embedding

L'indexeur appelle le point d'entrée api/embed du service, en passant une
liste de textes par lot. La réponse contient une liste de vecteurs dans le
même ordre que les textes envoyés. Le lot unique réduit le nombre
d'allers-retours réseau et accélère l'indexation d'un facteur notable par
rapport à un appel par chunk.

Le premier appel sur un modèle fraîchement téléchargé est plus lent que
les suivants, le temps de charger le modèle en mémoire. Les appels
ultérieurs bénéficient du modèle résident et durent une fraction de
seconde par lot. Ce comportement explique les temps très différents entre
une indexation à froid et une indexation où le modèle est déjà résident.