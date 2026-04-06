# TIMEASE - Générateur d'emploi du temps scolaire
Outil de génération automatique d'emplois du temps pour les écoles, basé sur Google OR-Tools CP-SAT.
## Installation
`uv sync`
## Lancement
`reflex run`

## Développement local (API + Frontend Next.js)
Lancer les deux services avec le script:

`./scripts/dev.sh`

Mode one-shot (sans watchers, utile si la machine fige en mode watch):

`./scripts/dev.sh --once`

Les logs d'exécution sont enregistrés automatiquement dans:

`logs/dev/`
