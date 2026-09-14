# Spécification de l'extension multi-projets

## Contexte et objectif

La stack RAG est née pour un seul projet. L'objectif est d'en faire une
plateforme personnelle : chaque projet de développement, dans son dossier
propre, dispose de ses connaissances et de ses mémoires vectorisées, sans
dupliquer l'infrastructure. Le portefeuille compte une vingtaine de projets ;
cette échelle impose de choisir une architecture délibérée plutôt que de
laisser la duplication s'installer.

## Décision : un hub central, des collections par projet

Une instance ChromaDB peut naturellement héberger plusieurs collections
indépendantes, chacune avec ses segments propres. Ces collections servent
ici de frontières logiques, pas de mécanisme de sécurité au sens fort —
ce document assume explicitement l'absence de cloisonnement côté MCP.
Il n'y a donc rien à multiplier : le hub garde un
serveur de base, un proxy MCP, une configuration Zed et un modèle
d'embedding uniques, et chaque projet devient une paire de collections.

L'alternative, une stack complète par projet, a été écartée pour un
développement personnel : elle multiplie les conteneurs, la mémoire
vive, les ports à arbitrer et les montées de version d'images par le
nombre de projets, pour un bénéfice d'isolation dont le besoin ne se
justifie pas ici. Elle reste l'exception documentée pour un projet
exigeant une isolation stricte des données ou vivant sur une autre
machine.

## Le routage, vraie difficulté de l'architecture

Deux propriétés du système déterminent le design. D'abord, le proxy
expose toutes les collections à toutes les conversations : aucune
configuration ne peut cloisonner au niveau du serveur MCP. Ensuite, une
requête s'adresse à une seule collection : il n'existe pas de recherche
inter-collections en un appel.

L'isolation repose donc sur deux mécanismes complémentaires : une
convention de nommage explicite, et une instruction de routage dans le
fichier AGENTS.md de chaque projet, qui désigne ses collections à
l'agent. C'est le même principe que le workflow mémoire : de la
discipline outillée, pas du cloisonnement matériel. La limite est assumée
et documentée : un agent distrait peut interroger la collection d'un
autre projet, et la clarté du nommage et des instructions en est la
principale parade.

## Convention de nommage

Chaque projet reçoit deux collections : le slug du projet suivi du
suffixe double souligné knowledge, puis le même slug suivi du suffixe
memories.

    cop_hierarchy__knowledge
    cop_hierarchy__memories
    mon-projet__knowledge
    mon-projet__memories

Le slug dérive du nom de dossier : minuscules, accents translittérés,
caractères limités aux lettres minuscules, chiffres, tirets et
soulignements, bornes alphanumériques, entre trois et soixante-trois
caractères au total, contraintes du serveur Chroma. Un dossier comme
2021_05_10_Spotiit donne un slug valide commençant par un chiffre.

Les collisions ne sont pas arbitrées à la main : si le slug dérivé du
dossier est déjà associé à un autre chemin, l'instanciation refuse
nettement et propose le slug déterministe dérivé du chemin canonique —
le slug suivi d'un double tiret et d'un hachage court du chemin. Deux
exécutions sur la même machine produisent ainsi toujours le même
résultat, sans résolution manuelle après coup.

## Mécanisme d'instanciation

Ce que chaque projet reçoit se réduit à quatre éléments textuels, sans
aucune infrastructure : un dossier docs pour le corpus, un dossier
memory optionnel pour ses mémoires, une section AGENTS.md de routage
désignant ses collections, et le manifeste d'identité .rag.yaml créé
par la première instanciation.

Le hub fournit un script unique qui, pour un chemin de projet donné,
calcule le slug, vérifie les contraintes, puis lance l'indexeur de
connaissances avec le dossier docs du projet monté en lecture seule et
la collection cible en variable d'environnement, puis l'indexeur de
mémoires si le dossier memory existe.

    ./index-project.sh <racine du projet>

Ces lancements se font par docker run direct sur l'image du hub, réseau
chroma-net, et non par compose run : les services compose montent déjà
le dossier docs du hub en dur, et les montages de ligne de commande
s'ajoutent sans remplacer.

La cohérence de l'embedding entre indexation et recherche est un
invariant explicite du mécanisme, pas une propriété automatique du
serveur MCP. À l'indexation, l'indexeur calcule les vecteurs avec
Ollama bge-m3 et enregistre cette fonction d'embedding dans la
configuration de la collection au moment de sa création. À la
recherche, chroma-mcp ne choisit aucun modèle : il recharge la fonction
enregistrée par la collection et encode la question dans le même
espace vectoriel. Le serveur MCP ne sait pas créer une collection avec
une fonction Ollama, et n'a pas besoin de le savoir : toute collection
du mécanisme naît déjà avec son invariant.

Cette mécanique impose une condition de déploiement : le paquet python
ollama reste présent dans l'environnement virtuel de chroma-mcp, sans
quoi l'indexation fonctionnerait mais toutes les requêtes échoueraient
au moment d'encoder la question. Le chemin question vers bge-m3 vers
Chroma est vérifié sur une collection jetable avant tout rollout, et
rejouable à volonté.

La configuration Zed reste unique et globale : elle pointe déjà sur le
proxy du hub, et le routage par projet se fait dans chaque AGENTS.md.

## Identité du projet et manifeste

Le slug est une propriété du projet, pas de son dossier. Dès la première
instanciation, un manifeste .rag.yaml est déposé à la racine du projet
et fait foi pour toutes les exécutions suivantes :

    project:
      manifest_version: 1
      slug: mon-projet

Le manifeste identifie le projet, il ne mémorise pas son emplacement
physique : le chemin courant est fourni au script à chaque exécution,
et le projet reste portable en Git. Renommer le dossier ne crée donc
jamais une seconde instance : le script lit le manifeste s'il existe,
et c'est lui, pas le nom du dossier, qui désigne les collections.
Seule la suppression délibérée du manifeste réinitialise l'identité RAG
du projet.

## Gabarit de routage projet

Chaque projet instancié reçoit une section standardisée dans son
AGENTS.md, qui transforme la visibilité totale des collections en
contrat opérationnel explicite :

    ## RAG local

    Ce projet utilise le hub RAG local.

    Collections :
    - connaissances : mon-projet__knowledge
    - mémoires : mon-projet__memories

    Recherche de connaissances du projet : exclusivement
    mon-projet__knowledge. Recherche de mémoire du projet :
    exclusivement mon-projet__memories. Aucune collection d'un autre
    projet sans demande explicite de l'utilisateur.

    Les mémoires durables suivent le workflow du hub : l'agent
    propose, l'humain valide, Git trace, puis le memory-indexer.

    Réindexation : /Users/michaelboitin/Documents/02_Dev/01_LocalRag_engine/AI/chroma/index-project.sh <racine du projet>

## Les mémoires

Chaque projet garde ses mémoires dans sa propre collection, avec le
workflow de proposition et validation humaine inchangé. Des préférences
transverses, comme le rythme de travail une étape à la fois, valent pour
tous les projets : une couche globale, une collection global memories
indexée depuis un dossier dédié du hub, pourra être ajoutée si la
duplication devient gênante. Elle n'est pas construite tant que le
besoin ne s'est pas fait sentir.

Le hub lui-même conserve ses collections actuelles, project_knowledge
et memories, sans migration : son AGENTS.md les désigne déjà. Un
renommage vers un namespace uniforme reste possible plus tard par une
simple modification de collection si le besoin d'homogénéité survient.

## Limites et risques

Toutes les collections restent visibles de toutes les conversations ;
la parade est la clarté du nommage et des instructions, pas un
cloisonnement serveur. Le hub est un point de défaillance unique : le
serveur de base tombé, le RAG est indisponible pour tous les projets ;
la politique de redémarrage et la sauvegarde du répertoire data
documentée au runbook couvrent ce risque.

Le coût réel est éditorial : un projet sans corpus docs est un RAG vide,
et la rédaction du corpus initial, assistée si besoin par l'agent à
partir du code, est le vrai travail d'adoption. Enfin, la recherche ne
croise pas les collections en un seul appel : croiser exige autant
d'appels que de collections, ce qui reste rarement nécessaire.

## Plan de déploiement

Le déploiement est incrémental, une étape à la fois. La première phase
outille le hub : cette spécification, le script d'instanciation, et le
gabarit de section AGENTS.md pour les projets. La deuxième phase valide
le mécanisme sur un seul projet pilote, avec son corpus initial, son
indexation et un test de requête routée de bout en bout. La troisième
phase ouvre le rollout à la demande : chaque projet supplémentaire est
instancié quand son corpus existe, jamais en masse — la valeur vient du
contenu réel, pas de collections vides.