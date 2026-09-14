# Architecture de Perchoir

Perchoir est un carnet d'observations d'oiseaux pour les bénévoles des
réserves. Chaque sortie enregistre un point de comptage, une heure et
une liste d'espèces ; tout se synchronise en différé à la fin de la
journée.

Le stockage local tient dans un fichier unique, recopié à chaque
enregistrement : aucune base distante n'est requise sur le terrain, et
la perte du réseau n'interrompt jamais la saisie.

L'identification des espèces repose sur un catalogue embarqué de mille
deux cents fiches, consultable hors connexion, mis à jour une fois par
an par le conservatoire.