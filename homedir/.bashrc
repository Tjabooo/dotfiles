#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias py='python'
alias restart-wifi='nmcli radio wifi off && sleep 2 && nmcli radio wifi on'
alias fetch='clear && fastfetch --config ~/.config/fastfetch/homer.jsonc'
alias editconf='nano ~/.config/hypr/hyprland.conf'
alias zed='/usr/bin/zeditor'
alias basher='nano ~/.bashrc'
alias spotify-run='spotify --useFeatures=UseOzonePlatform --ozone-platform=wayland'
alias batteryhealth='upower -i /org/freedesktop/UPower/devices/battery_BAT0 | grep -E "capacity|energy"'
alias vencord='sh -c "$(curl -sS https://raw.githubusercontent.com/Vendicated/VencordInstaller/main/install.sh)"'
alias disable-sleep='systemd-inhibit --what=idle:sleep --why="Temporary disable sleep" bash'

PS1='[\u@\h \W]\$ '
eval "$(~/.local/bin/oh-my-posh init bash --config ~/amro.omp.json)"
fastfetch --config ~/.config/fastfetch/cat.jsonc
source ~/workspace/venv/global/bin/activate
export PATH=$PATH:/home/tjaboobies/.spicetify

