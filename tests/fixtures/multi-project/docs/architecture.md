# Architecture de Lumen

Lumen est une application de listes de lecture hors ligne. Les données
vivent dans une base SQLite locale, sans serveur distant : la lecture et
l'ajout de livres fonctionnent sans aucune connexion.

La synchronisation est délibérément restrictive : Lumen ne synchronise
ses listes que lorsque l'appareil est connecté en wifi, jamais en
réseau mobile, pour épargner le forfait de données de l'utilisateur.

L'interface affiche trois écrans : la bibliothèque, la pile à lire, et
les statistiques annuelles. Chaque écran lit directement la base
locale, sans couche réseau intermédiaire. Un mode nuit teinte l'écran
en sépia après vingt-deux heures.