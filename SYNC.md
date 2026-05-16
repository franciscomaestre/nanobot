# Estrategia de ramas

## Estructura

- **`main`** → sincronizada con upstream (HKUDS/nanobot). No hacer commits propios aquí.
- **`claudio`** → rama de trabajo con nuestros cambios propios.

## Sincronizar con upstream

Cuando haya novedades en el repo original:

```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main

# Actualizar claudio con los cambios de main
git checkout claudio
git rebase main
git push origin claudio --force-with-lease
```

## Remotes

- `origin` → git@bitbucket.org:data-fact/data-fact-nanobot.git (nuestro repo)
- `upstream` → https://github.com/HKUDS/nanobot.git (repo original)
