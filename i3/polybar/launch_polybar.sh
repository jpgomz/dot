#!/bin/bash

# Matar instancias previas
killall -q polybar

# Esperar a que se cierren
while pgrep -x polybar >/dev/null; do sleep 0.1; done

# Detectar el monitor primario con xrandr
PRIMARY_MONITOR=$(xrandr --query | awk '/ connected primary/ {print $1}')

# Lanzar solo en el monitor primario
if [[ -n "$PRIMARY_MONITOR" ]]; then
	MONITOR=$PRIMARY_MONITOR polybar --reload toph &
else
	echo "No se detectó un monitor primario"
fi