# Démonstration : un freinage, une panne 4G, puis la reprise

Le projet reprend les fonctions des PowerPoint OK6 (diapositives 32 à 38) et OK7 (diapositives 36 à 42), avec leurs noms. La collecte utilise le moteur Safety existant. Seul l'envoi tourne dans un thread séparé.

Le lanceur Safety retrouve le déroulé du projet d'origine : lire les mesures, détecter les freinages, écrire le bilan. L'ajout utile est on_event=save_alert, qui enregistre chaque freinage dès sa détection. Le bilan JSON conserve uniquement les freinages de cet essai, pas toutes les mesures.

Le type explicite du freinage est repris du fichier src/domain/telemetry_event.py de la pièce jointe d’origine. Le JSON enregistré puis envoyé porte event_type="harsh_braking" pour un freinage et event_type="zfe_entry" pour une entrée en ZFE. save_alert() ajoute le type du freinage par défaut et conserve tout type déjà fourni, puis ajoute l’UUID et l’heure de capture.

## Lancer et présenter

Avec Python 3.11 ou plus récent installé, extraire le ZIP, lancer INSTALLER.bat une fois, puis LANCER_PROJET.bat. Le lanceur exécute run_bloc3_demo.py.

Le scénario dure environ dix secondes et se déroule automatiquement.

1. sensor_samples() fournit 100 mesures, à une cadence d’environ 100 ms. Les dix premières viennent de data/accelerometer_data.csv et contiennent un seul freinage. Les suivantes sont normales, avec acc_y=0 : la collecte continue sans créer un autre freinage.
2. acquisition_loop() transmet ce flux à Safety par le paramètre samples. Le moteur existant détecte le freinage et appelle save_alert(). L’alerte est enregistrée dans SQLite ; les premiers envois échouent, car la 4G simulée est coupée.
3. Toutes les dix mesures, une ligne [COLLECTE] affiche le nombre de mesures lues, l’état de la 4G et le nombre d’alertes en attente. Le compteur continue d’avancer pendant la panne.
4. À la mesure 61, vers six secondes, la 4G simulée revient automatiquement. Le thread renvoie la même alerte puis la supprime après le succès, pendant que la collecte poursuit ses mesures jusqu’à 100.

**Bilan attendu : 100 mesures, 1 freinage et 0 alerte en attente.** SQLite est réel. La panne réseau et la réception distante sont simulées. Les résultats restent dans un nouveau dossier resultats_demo/essai-... à chaque essai.

## Les fonctions à montrer dans les sources

| Fonction | Fichier du projet | Rôle |
|---|---|---|
| sensor_samples() — démonstration | run_bloc3_demo.py | Fournit les 100 mesures cadencées, affiche la progression et rétablit la 4G simulée à la mesure 61. |
| acquisition_loop() | run_demo.py | Transmet le flux samples à Safety avec on_event=save_alert : chaque freinage détecté est enregistré dans le thread principal. |
| initialize_database(), save_alert() | src/storage/event_repository.py | Préparent SQLite et enregistrent l'alerte avant tout envoi. |
| get_pending_alerts(), schedule_retry() | src/storage/event_repository.py | Relisent les alertes à envoyer et enregistrent la prochaine tentative en cas d'échec. |
| network_worker() | src/sync/sync_service.py | Envoie les alertes dans le thread réseau. |
| delete_alert() | src/storage/event_repository.py | Supprime l'alerte après un envoi réussi. |

Le cœur de network_worker() suit le try/except/else des PPT :

```python
for alert_id, payload, attempts in pending_alerts:
    try:
        send_alert(alert_id, payload)
    except requests.RequestException:
        schedule_retry(alert_id, attempts)
    else:
        delete_alert(alert_id)
```

**Store and forward** signifie ici : enregistrer d'abord dans SQLite, puis envoyer dès que le réseau le permet. L'envoi ne bloque pas la collecte, car il tourne dans son propre thread. Aucun circuit breaker n'est utilisé.

Les tentatives sont espacées de 2, 4, 8 secondes, jusqu'à 300 secondes. Le nombre d'essais et la date de la prochaine tentative restent dans SQLite. Pour la présentation, run_bloc3_demo.py plafonne ce délai à 2 secondes.

## Où est l'appel à l'API ?

Dans send_alert(), fichier src/sync/sync_service.py. La branche de démonstration simule le résultat ; l'autre branche contient requests.post(). Pour utiliser une API réelle, renseigner GML_API_URL et GML_API_TOKEN, puis lancer run_demo.py. Ce lanceur conserve aussi la collecte Geo du projet. L'option --sync-only reprend les alertes déjà stockées.

Un succès HTTP 2xx autorise la suppression. Le même UUID est envoyé dans le JSON et dans Idempotency-Key à chaque tentative ; la déduplication dépend de l'API destinataire.

Cette version utilise la table pending_alerts. Les anciennes lignes d'une table events ne sont pas migrées ni envoyées par ce flux.

LANCER_TESTS.bat lance les tests. Le résultat réel des vérifications figure dans VALIDATION.txt.

## Ajout de la chaîne CI/CD

Le guide [CI_CD_DEMO.md](CI_CD_DEMO.md) décrit les étapes et les fichiers à montrer.

Le workflow `.github/workflows/bloc3-ci.yml` contrôle le code, lance les tests et les analyses de sécurité, puis construit le paquet avec `scripts/build_package.py`. `scripts/staging_demo.py` exécute les sources extraites de ce paquet et vérifie la collecte, la reprise réseau, le rollback simulé et l'installation réussie.

Le workflow `.github/workflows/promote-demo.yml` permet ensuite de choisir manuellement une CI réussie et de promouvoir exactement son paquet validé. Le simulateur OTA vérifie son SHA-256 avant de modifier l'état local.

Pour présenter le build et le staging sans GitHub : lancer **LANCER_LIVRAISON.bat** après INSTALLER.bat. Les résultats se trouvent dans `dist/` et `staging/`. La logique Safety, Geo, SQLite et d'envoi reste celle décrite ci-dessus.

## Priorites demo - memoire bornee et backoff visible
- Historique capteurs en RAM borne avec `deque(maxlen=600)` dans `run_demo.py`.
- La demo affiche une preuve simple : 1 000 mesures injectees, buffer limite a 600/600.
- Le retry/backoff affiche maintenant les delais reels : 2 s, 4 s, 8 s, etc.
- La panne 4G est maintenue assez longtemps pour montrer 2 s, 4 s et 8 s avant la reprise.
- Verification : 42 tests passent.
