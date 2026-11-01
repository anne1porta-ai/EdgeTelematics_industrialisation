# Bloc 3 — fonctionnement technique

## 1. Correction des deux causes de crise

Le code initial avait deux défauts : une liste mémoire non bornée et un appel réseau dans la boucle capteur.

La version actuelle sépare trois responsabilités :

```text
collecte capteur
→ stockage SQLite
→ worker réseau
```

La collecte ne fait aucun appel HTTP.

## 2. Mémoire bornée

`run_demo.py` utilise :

```python
recent_samples = deque(maxlen=600)
```

Même après 1 000 mesures, la RAM conserve au maximum 600 échantillons récents. Les alertes importantes sont, elles, écrites dans SQLite.

## 3. Événements métier

`TelemetryEvent` définit deux types simples :

- `harsh_braking` ;
- `zfe_entry`.

Chaque alerte reçoit un UUID stable lors de son premier enregistrement.

## 4. SQLite et historique

`src/storage/event_repository.py` fournit :

| Fonction | Rôle |
|---|---|
| `initialize_database()` | Créer `pending_alerts` et `event_history`. |
| `save_alert()` | Écrire l'alerte avant tout appel réseau. |
| `get_pending_alerts()` | Lire les alertes prêtes à être envoyées. |
| `schedule_retry()` | Enregistrer le prochain essai. |
| `mark_alert_synced()` | Archiver avec `synced=1`, puis retirer de la file active. |
| `pending_count()` | Compter la file active. |
| `synced_count()` | Compter l'historique synchronisé. |

SQLite est configuré en mode WAL.

## 5. Worker réseau

`src/sync/sync_service.py` applique une logique directe :

```text
lire une alerte
→ tenter l'envoi
→ échec : conserver et programmer un retry
→ succès : archiver avec synced=1
```

Les délais sont `2 s, 4 s, 8 s...`, plafonnés à 300 secondes.

Le client HTTP utilise :

- `Authorization: Bearer ...` ;
- `Idempotency-Key` ;
- `timeout=(3, 10)`.

Il n'y a pas de circuit breaker dans ce POC.

## 6. Démonstration de crise

`run_bloc3_demo.py` traite 160 mesures :

1. 1 000 mesures sont injectées dans le buffer pour prouver la limite `600/600` ;
2. la 4G est coupée ;
3. Safety détecte un freinage et le stocke ;
4. le worker affiche les retries `2 s, 4 s, 8 s` ;
5. la collecte continue ;
6. la 4G revient ;
7. l'alerte est archivée après succès ;
8. une API locale démontre le timeout puis l'idempotence.

Résultat attendu :

```text
160 mesures
1 freinage
0 alerte en attente
1 alerte historisée avec synced=1
```

## 7. Tests

```powershell
.\LANCER_TESTS_CRISE.bat
.\LANCER_TESTS.bat
```

Les tests de crise prouvent notamment : mémoire bornée, découplage réseau, persistance avant envoi, conservation après échec, purge après succès, HTTPS, authentification, idempotence et timeout.

## 8. OTA

Le paquet historique `src/ota/packages/greenmove-2.3.0.pkg` est conservé pour les tests pédagogiques.

La chaîne GitHub construit en plus un ZIP, calcule son SHA-256, le signe avec une clé privée stockée dans GitHub Secrets et vérifie la signature avec `keys/ota_public.pem`.

Le staging exécute le code extrait du ZIP, vérifie le scénario `160 / 1 / 0 / 1`, simule un échec avec rollback, puis installe le même paquet avec succès.

## 9. Promotion

Une promotion ne reconstruit rien. Le workflow manuel récupère `greenmove-validated-package` depuis un run CI vert, revérifie hash et signature, puis simule :

```text
10 interne
→ 50 pilote
→ 250
→ 1 000
→ NO-GO
→ gel
→ rollback N-1
```
