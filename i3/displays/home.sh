#!/bin/bash

# Configurar displays
xrandr \
	--output eDP-1 --off \
	--output HDMI-1 --primary --mode 1600x900 --pos 895x1050 --rotate normal \
	--output DP-1 --mode 1680x1050 --pos 0x0 --rotate normal \
	--output DP-2 --mode 1680x1050 --pos 1680x0 --rotate normal

# Esperar a que i3 termine de reconfigurar las salidas
for i in {1..10}; do
	i3-msg -t get_workspaces | grep -q output && break
	sleep 0.2
done

# Función para asignar workspaces
assign_workspace() {
	i3-msg "workspace $1; move workspace to output $2"
}

# Asignar workspaces
assign_workspace 1 HDMI-1
assign_workspace 2 HDMI-1
assign_workspace 3 DP-1
assign_workspace 4 DP-1
assign_workspace 5 DP-2
assign_workspace 6 DP-2

# Ir al workspace principal
i3-msg "workspace 1"

# Notificación
notify-send -i video-display "Layout aplicado: Casa"
