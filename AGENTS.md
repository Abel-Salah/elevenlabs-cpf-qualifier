

## Référentiel transversal PROJECT-RULES

Avant toute intervention transverse (machines, runners, SSH/Tailscale, stockage, sauvegardes, CI, hébergement ou coûts), lire les fichiers applicables sur la branche `main` de [Abel-Salah/PROJECT-RULES](https://github.com/Abel-Salah/PROJECT-RULES/tree/main) :

- `AGENTS.md`
- `CONFIGURATION.md`
- `PR-LIFECYCLE.md`
- `CI-COST-POLICY.md`
- `INFRA-OPS.md`
- `HOSTING.md`
- `docs/quality/README.md`
- `docs/projects/ELEVENLABS-CPF-QUALIFIER.md`

Puis lire les règles locales de ce dépôt. Les règles locales spécifiques au code, aux données, au produit et aux releases restent prioritaires lorsqu'elles sont plus précises. Les contrôles exécutables restent dans ce dépôt. Ne jamais utiliser une règle provenant d'une branche ou d'une PR non mergée.
