#!/bin/bash

# laptop.sh - Configuración para laptop solo
#!/bin/bash

# Configurar displays
xrandr --output eDP-1 --primary --mode 1280x720 --pos 0x0 --rotate normal \
	--output HDMI-1 --off \
	--output HDMI-2 --off \
	--output DP-1 --off \
	--output DP-2 --off

# Función para asignar workspaces
assign_workspace() {
	i3-msg "workspace $1; move workspace to output $2"
}

# Asignar workspaces
assign_workspace 1 eDP-1
assign_workspace 2 eDP-1
assign_workspace 3 eDP-1
assign_workspace 4 eDP-1
assign_workspace 5 eDP-1
assign_workspace 6 eDP-1
assign_workspace 7 eDP-1
assign_workspace 8 eDP-1
assign_workspace 9 eDP-1
assign_workspace 10 eDP-1

# Ir al workspace 1
i3-msg "workspace 1"

# Notificación
notify-send -i video-display "Layout aplicado: Laptop"
