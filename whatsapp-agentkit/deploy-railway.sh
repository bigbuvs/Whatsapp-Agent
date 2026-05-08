#!/bin/bash
set -e

echo "=========================================="
echo "  Atlas — Deploy automático a Railway"
echo "=========================================="

# Cargar variables desde .env
if [ ! -f .env ]; then
  echo "Error: no se encontró .env en este directorio."
  echo "Ejecuta este script desde whatsapp-agentkit/"
  exit 1
fi
export $(grep -v '^#' .env | grep -v '^$' | xargs)

# Instalar Railway CLI si no está
if ! command -v railway &> /dev/null; then
  echo "[1/5] Instalando Railway CLI..."
  npm install -g @railway/cli
else
  echo "[1/5] Railway CLI ya instalado"
fi

# Login con token (pasado como argumento o variable de entorno)
RAILWAY_TOKEN="${1:-$RAILWAY_TOKEN}"
if [ -z "$RAILWAY_TOKEN" ]; then
  echo "Error: necesitas pasar tu Railway token."
  echo "Uso: bash deploy-railway.sh <TU_RAILWAY_TOKEN>"
  exit 1
fi
export RAILWAY_TOKEN

echo "[2/5] Autenticando en Railway..."
railway whoami

# Crear proyecto
echo "[3/5] Creando proyecto Atlas..."
railway init --name "atlas-agent"

# Configurar variables de entorno desde .env
echo "[4/5] Configurando variables de entorno..."
railway variables set \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  WHATSAPP_PROVIDER="$WHATSAPP_PROVIDER" \
  TWILIO_ACCOUNT_SID="$TWILIO_ACCOUNT_SID" \
  TWILIO_AUTH_TOKEN="$TWILIO_AUTH_TOKEN" \
  TWILIO_PHONE_NUMBER="$TWILIO_PHONE_NUMBER" \
  PORT="8000" \
  ENVIRONMENT="production" \
  DATABASE_URL="sqlite+aiosqlite:///./agentkit.db"

# Deploy
echo "[5/5] Desplegando Atlas..."
railway up --detach

echo ""
echo "=========================================="
echo "  Deploy completado."
echo "=========================================="
railway domain
