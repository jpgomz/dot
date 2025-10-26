#!/bin/bash

# Detectar salidas conectadas
OUTPUTS=$(xrandr | grep " connected" | cut -d" " -f1 | sort | tr '\n' ' ')

# Función para comparar salidas conectadas
has_outputs() {
  for output in "$@"; do
    echo "$OUTPUTS" | grep -q "$output" || return 1
  done
  return 0
}

# Ruta base de los scripts
LAYOUT_DIR="$HOME/.config/i3/displays"

# Lógica de detección
if has_outputs DP-1 DP-2 HDMI-1; then
  bash "$LAYOUT_DIR/home.sh"
  notify-send -i video-display "Layout detectado: Casa"
elif has_outputs DP-1 DP-2 HDMI-1 eDP-1; then
  bash "$LAYOUT_DIR/office.sh"
  notify-send -i video-display "Layout detectado: Oficina"
elif has_outputs eDP-1 && ! echo "$OUTPUTS" | grep -q -E "DP|HDMI"; then
  bash "$LAYOUT_DIR/laptop.sh"
  notify-send -i video-display "Layout detectado: Solo Laptop"
else
  # Fallback por si cambia algo inesperadamente
  bash "$LAYOUT_DIR/laptop.sh"
  notify-send -i dialog-warning "Layout desconocido, usando Laptop"
fi

