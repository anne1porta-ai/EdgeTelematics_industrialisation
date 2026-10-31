# Dossiers 4 et 5 — Guide de demonstration

Ce dossier contient le code existant de la version enrichie de GreenMove Edge. Les deux moteurs du dossier 4 ont ete conserves. Les fonctions SQLite, synchronisation et OTA sont des extensions, non des preuves de deploiement industriel.

## Conditions

Python >= 3.10, aucun service externe requis pour la demonstration. Depuis la racine :

```bash
python -m pip install -r requirements.txt
python run_demo.py
python run_demo.py --stress
python -m pytest -q
python run_bloc3_demo.py
```

## Resultats verifies le 13 octobre 2026

- Alerte ZFE : point GPS id=4, timestamp 08:00:30.
- Freinage : acc_y=-3.45 m/s2 a 1678880005.
- Jeu a 100 Hz simules : 1000 echantillons, 1 evenement.
- Tests : 27 passed.
- Synchronisation simulee : evenement pending=1 sans reseau, pending=0 apres retour.

## Deux points a expliquer

1. La colonne `expected` du point GPS n°3 dit « IN », alors que ce point est geométriquement hors du polygone fourni. Le moteur ne modifie pas ce resultat.
2. L'enonce mentionne 2,5 G mais son annexe impose le seuil longitudinal de -2,5 m/s2. Le moteur utilise les m/s2 du CSV.

## Limites explicites

- Aucun test sur une tablette Zebra ET40 reelle n'a ete effectue ici.
- La zone de Lyon utilisee est un polygone simplifie ; la cartographie europeenne n'est pas fournie.
- Le mode 100 Hz est une generation de donnees a timestamps simules, non une acquisition capteur.
- La coupure/retour reseau sont simules avec des fonctions locales, pas avec la 4G reelle.
- Les messages compacts/compression du reseau sont une architecture cible non livree dans ce code.
- Le rabais d'assurance de 20 % n'est pas valide par l'assureur.

Depot mentionne par le projet : https://github.com/MyriamKuhn/greenmove-edge-poc.git. Verifier que la version du depot distant correspond bien aux archives avant remise.
