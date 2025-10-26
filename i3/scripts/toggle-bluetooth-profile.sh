#!/bin/bash

# Detecta el card Bluetooth automáticamente
CARD_NAME=$(pactl list short cards | grep bluez_card | awk '{print $2}')

# Obtener el perfil actual
CURRENT_PROFILE=$(pactl list cards | grep -A20 "$CARD_NAME" | grep "Active Profile" | awk -F: '{print $2}' | xargs)

if [[ "$CURRENT_PROFILE" == "headset-head-unit-msbc" ]]; then
	# Pasar a modo música
	pactl set-card-profile "$CARD_NAME" a2dp-sink-aptx
	notify-send "Audio Bluetooth" "🎧 Modo música activado (A2DP aptX)"
else
	# Pasar a modo headset con micrófono
	pactl set-card-profile "$CARD_NAME" headset-head-unit-msbc
	notify-send "Audio Bluetooth" "🎙️ Modo micrófono activado (HSP mSBC)"
fi
