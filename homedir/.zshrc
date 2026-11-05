source ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh

# Aliases
alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias py='python'
alias restart-wifi='nmcli radio wifi off && sleep 2 && nmcli radio wifi on'
alias editconf='nvim ~/.config/hypr/hyprland.lua'
alias reload='hyprctl reload && hyprctl configerrors'
alias update='neon-update'          # Arch news → yay -Syu → .pacnew → orphans → reboot hint
alias keys='neon-keys --print'
alias logout="systemctl --user stop neon-session.target; hyprctl dispatch 'hl.dsp.exit()'"
alias zed='/usr/bin/zeditor'
alias claude2='CLAUDE_CONFIG_DIR=$HOME/.claude-2 claude'   # second Claude Pro account (shares ~/.claude via agent-mesh)
alias basher='nvim ~/.zshrc'
alias spotify-run='spotify --useFeatures=UseOzonePlatform --ozone-platform=wayland'
alias batteryhealth='upower -i /org/freedesktop/UPower/devices/battery_BAT0 | grep -E "capacity|energy"'
alias vencord='sh -c "$(curl -sS https://raw.githubusercontent.com/Vendicated/VencordInstaller/main/install.sh)"'
alias disable-sleep='systemd-inhibit --what=idle:sleep --why="Temporary disable sleep" bash'
alias pear2pear-send='java -cp /home/tjabo/workspace/pear2pear/src pear2pear.Pear server'
alias restart-waybar='~/.config/hypr/scripts/restart_waybar'
alias nightmode='brightnessctl s 2500'
alias chat='chatgpt --ozone-platform=wayland'

# Oh My Posh prompt (Zsh)
eval "$(~/.local/bin/oh-my-posh init zsh --config ~/.config/ohmyposh/midnight-neon.omp.json)"

# Default editor
export EDITOR=nvim

# Fastfetch
fastfetch

# Python venv
# source ~/workspace/venv/bin/activate  # commented out by conda initialize

# PATH additions
export PATH=$PATH:/home/tjabo/.spicetify

function y() { local t="$(mktemp)"; yazi "$@" --cwd-file="$t"; local d="$(cat "$t")"; [ -n "$d" ] && [ "$d" != "$PWD" ] && cd "$d"; rm -f "$t"; }

# pyenv 3.12.3
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

HISTFILE=~/.zsh_history
HISTSIZE=50000
SAVEHIST=50000

setopt APPEND_HISTORY
setopt SHARE_HISTORY          # every terminal sees the others' commands right away
setopt HIST_IGNORE_ALL_DUPS   # no duplicate entries
setopt HIST_IGNORE_SPACE      # a command starting with a space isn't saved (tokens, passwords)
setopt HIST_REDUCE_BLANKS
bindkey -e                                # emacs keys (Ctrl+R search, Ctrl+A/E)
bindkey '^[[A' history-search-backward    # ↑ / ↓ complete from history
bindkey '^[[B' history-search-forward
bindkey '^[[1;5C' forward-word            # Ctrl+→ accepts one word of a suggestion
bindkey '^[[1;5D' backward-word
ZSH_AUTOSUGGEST_STRATEGY=(history)
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#6c6c8a'

# zoxide: `z proj` jumps to the best-matching dir you've visited, `zi` picks interactively
command -v zoxide >/dev/null && eval "$(zoxide init zsh)"
# pkgfile: unknown command → tells you which package provides it
[[ -r /usr/share/doc/pkgfile/command-not-found.zsh ]] && source /usr/share/doc/pkgfile/command-not-found.zsh

# oh-my-zsh plugins
source ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

conda() {
    unset -f conda
    . "$HOME/miniforge3/etc/profile.d/conda.sh"
    conda "$@"
}

# miniforge is NOT on PATH (its base python used to shadow pyenv + system python everywhere,
# systemd included). `conda activate <env>` still works: the conda() function above loads it.

# Created by `pipx` on 2026-08-26 10:16:11
export PATH="$PATH:/home/tjabo/.local/bin"
