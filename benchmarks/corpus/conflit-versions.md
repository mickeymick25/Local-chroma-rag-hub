# Le conflit de versions MCP et sa résolution

## Le diagnostic

Le proxy MCP en version 0.12.0 exige un SDK MCP de version supérieure ou
égale à 1.17. Le serveur chroma-mcp en version 0.2.6 impose au contraire un
pin strict sur la version 1.6.0 du même SDK. Les deux exigences sont
incompatibles : aucun environnement Python unifié ne peut satisfaire les
deux programmes à la fois.

Tenter d'installer les deux dans le même environnement dégrade l'un des
deux : le gestionnaire de paquets écrase la version du SDK, et le programme
dont l'exigence n'est plus satisfaite casse au lancement. Le conflit est
donc structurel, pas un accident d'installation.

## La résolution : deux environnements dans un conteneur

Le conteneur du proxy embarque deux environnements Python étanches.
L'environnement système porte le proxy et la version 1.27.2 du SDK MCP. Un
environnement virtuel dédié sous opt/chroma-mcp porte chroma-mcp et la
version 1.6.0 du SDK.

Un petit script wrapper, posé dans le répertoire des exécutables système,
redirige la commande chroma-mcp vers le binaire de l'environnement virtuel.
Le proxy lance ce wrapper comme processus enfant sans connaître le détail
de l'isolation.

La frontière entre les deux mondes est le protocole stdio : le proxy et son
serveur aval échangent du JSON-RPC ligne par ligne sur des tubes, jamais
par l'API Python. C'est ce qui rend la cohabitation sûre : aucune version
de bibliothèque ne peut contaminer l'autre.

## Le paquet ollama dans l'environnement virtuel

L'environnement virtuel contient un point souvent négligé : le paquet
python ollama. La fonction d'embedding Ollama de chromadb délègue en effet
à ce paquet, et le venv de chroma-mcp doit l'embarquer pour pouvoir encoder
les textes de recherche envoyés par l'agent.

Sans ce paquet, les écritures de l'indexeur fonctionnent, car elles
fournissent leurs vecteurs explicitement, mais toutes les requêtes de
l'agent échouent au moment d'encoder la question. La panne serait
asymétrique et difficile à diagnostiquer sans connaître ce mécanisme.

## Vérifier les versions

La validation s'automatise : une commande docker run par interpréteur
affiche la version effective du SDK MCP dans chaque environnement. Le
résultat attendu est 1.27.2 côté système et 1.6.0 côté environnement
virtuel, une paire qui prouve que l'isolation tient après toute
reconstruction d'image.