#!/bin/sh

echo "[Entrypoint] Préparation du dossier /data..."
mkdir -p /data
chmod 777 /data 2>/dev/null || echo "[WARN] chmod ignoré (non-root)"

echo "[Entrypoint] Migration base de données..."
doccano migrate

echo "[Entrypoint] Création de l'utilisateur admin..."
doccano create_admin \
  --username "$ADMIN_USERNAME" \
  --password "$ADMIN_PASSWORD" \
  --email "$ADMIN_EMAIL" || true

echo "[Entrypoint] Lancement du serveur web..."
exec doccano webserver
