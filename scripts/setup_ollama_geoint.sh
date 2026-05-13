#!/usr/bin/env bash
# =============================================================================
#  setup_ollama_geoint.sh
#  Instala y configura Ollama con el modelo de análisis geopolítico.
#  Compatible con: Ubuntu 22.04+, Debian 12+, RHEL 9+
# =============================================================================
set -euo pipefail

GEOINT_MODEL="${GEOINT_LLM_MODEL:-gemma4:4b}"
OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
MODELFILE_PATH="$(dirname "$0")/../config/ollama_geoint.modelfile"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

echo "======================================================"
echo "  ATALAYA — CONFIGURACIÓN DE OLLAMA PARA GEOINT"
echo "======================================================"
echo "  Modelo objetivo: ${GEOINT_MODEL}"
echo "  Host Ollama:     ${OLLAMA_HOST}"
echo "======================================================"

# --- 1. Instalar Ollama si no está presente ---
if ! command -v ollama &>/dev/null; then
    warn "Ollama no encontrado. Instalando..."
    if command -v curl &>/dev/null; then
        curl -fsSL https://ollama.com/install.sh | sh
    else
        err "curl no disponible. Instala Ollama manualmente desde https://ollama.com"
    fi
    log "Ollama instalado."
else
    log "Ollama ya instalado: $(ollama --version)"
fi

# --- 2. Configurar variables de entorno de seguridad ---
OLLAMA_ENV_FILE="/etc/systemd/system/ollama.service.d/geoint.conf"
if command -v systemctl &>/dev/null && systemctl is-active --quiet ollama 2>/dev/null; then
    warn "Aplicando hardening de Ollama..."
    sudo mkdir -p "$(dirname "$OLLAMA_ENV_FILE")"
    sudo tee "$OLLAMA_ENV_FILE" > /dev/null <<EOF
[Service]
Environment="OLLAMA_HOST=${OLLAMA_HOST}"
Environment="OLLAMA_ORIGINS="
Environment="OLLAMA_DEBUG=0"
EOF
    sudo systemctl daemon-reload
    sudo systemctl restart ollama
    sleep 3
    log "Servicio Ollama reiniciado con configuración hardened."
else
    warn "systemd no disponible o Ollama no corre como servicio. Configura manualmente:"
    echo "  export OLLAMA_HOST=${OLLAMA_HOST}"
    echo "  export OLLAMA_ORIGINS=''"
    echo "  export OLLAMA_DEBUG=0"
fi

# --- 3. Verificar que Ollama responde ---
OLLAMA_API="http://${OLLAMA_HOST}/api/tags"
for i in 1 2 3 4 5; do
    if curl -fsS "$OLLAMA_API" >/dev/null 2>&1; then
        log "Ollama API responde en ${OLLAMA_HOST}."
        break
    fi
    warn "Esperando Ollama (intento $i/5)..."
    sleep 3
    [[ $i -eq 5 ]] && err "Ollama no responde en ${OLLAMA_HOST}. Inicia el servicio y reintenta."
done

# --- 4. Descargar modelo base ---
log "Descargando modelo base: ${GEOINT_MODEL}"
ollama pull "${GEOINT_MODEL}"
log "Modelo ${GEOINT_MODEL} disponible."

# --- 5. Crear modelo personalizado para análisis geopolítico ---
if [[ ! -f "$MODELFILE_PATH" ]]; then
    warn "Modelfile no encontrado en ${MODELFILE_PATH}. Creando en config/ollama_geoint.modelfile..."
    mkdir -p "$(dirname "$MODELFILE_PATH")"
    cat > "$MODELFILE_PATH" <<'MODELFILE'
FROM gemma4:4b

PARAMETER temperature 0.2
PARAMETER num_ctx 8192
PARAMETER num_predict 2500
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1

SYSTEM """Eres un analista de inteligencia estratégica militar con especialización en
geopolítica, defensa, seguridad internacional y economía política global.

PRINCIPIOS OPERATIVOS:
- Responde siempre en español profesional, terminología estándar NATO/ONU
- Estructura los informes con secciones Markdown jerarquizadas
- Cita la fuente de cada afirmación cuando esté disponible
- Marca niveles de confianza: [CONFIRMADO / PROBABLE / POSIBLE / NO CONFIRMADO]
- Prioriza precisión y objetividad sobre creatividad
- Distingue entre hechos, análisis y recomendaciones
- Evalúa siempre el impacto para Iberoamérica cuando sea relevante
"""
MODELFILE
fi

# Ajustar nombre del modelo base en el Modelfile si es diferente al default
sed -i "s|^FROM .*|FROM ${GEOINT_MODEL}|" "$MODELFILE_PATH"

log "Creando modelo personalizado 'atalaya-geoint'..."
ollama create atalaya-geoint -f "$MODELFILE_PATH"
log "Modelo 'atalaya-geoint' creado y listo."

# --- 6. Verificación de funcionamiento ---
echo ""
echo "======================================================"
echo "  VERIFICACIÓN DE FUNCIONAMIENTO"
echo "======================================================"
TEST_RESPONSE=$(ollama run atalaya-geoint "Di 'SISTEMA OPERATIVO' en 5 palabras." 2>&1 | head -3)
if [[ -n "$TEST_RESPONSE" ]]; then
    log "Modelo responde correctamente:"
    echo "  → $TEST_RESPONSE"
else
    warn "No se obtuvo respuesta de prueba. Verifica manualmente: ollama run atalaya-geoint"
fi

echo ""
echo "======================================================"
echo "  CONFIGURACIÓN COMPLETADA"
echo "======================================================"
echo ""
echo "  Modelo listo:     atalaya-geoint"
echo "  Basado en:        ${GEOINT_MODEL}"
echo "  Endpoint:         http://${OLLAMA_HOST}"
echo ""
echo "  Para generar un informe semanal:"
echo "  python scripts/run_weekly_geoint.py --model atalaya-geoint"
echo ""
echo "  Para configurar generación automática (cron):"
echo "  0 6 * * MON python /ruta/scripts/run_weekly_geoint.py >> /var/log/geoint.log 2>&1"
echo "======================================================"
