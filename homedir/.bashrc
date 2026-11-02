#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias py='python'
alias restart-wifi='nmcli radio wifi off && sleep 2 && nmcli radio wifi on'
alias fetch='clear && fastfetch'
alias editconf='nano ~/.config/hypr/hyprland.lua'
alias zed='/usr/bin/zeditor'
alias basher='nano ~/.bashrc'
alias spotify-run='spotify --enable-features=UseOzonePlatform --ozone-platform=wayland'
alias batteryhealth='upower -i /org/freedesktop/UPower/devices/battery_BAT0 | grep -E "capacity|energy"'
alias vencord='sh -c "$(curl -sS https://raw.githubusercontent.com/Vendicated/VencordInstaller/main/install.sh)"'
alias disable-sleep='systemd-inhibit --what=idle:sleep --why="Temporary disable sleep" bash'

PS1='[\u@\h \W]\$ '
eval "$(~/.local/bin/oh-my-posh init bash --config ~/.config/ohmyposh/midnight-neon.omp.json)"
fastfetch
# source ~/workspace/venv/bin/activate  # commented out by conda initialize
export PATH=$PATH:/home/tjabo/.spicetify

# pyenv 3.12.3
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"


# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/home/tjabo/miniconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/home/tjabo/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/home/tjabo/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/home/tjabo/miniconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

