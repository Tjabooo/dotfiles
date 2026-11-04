-- ~/.config/nvim/init.lua  —  "midnight neon" on unit-01, "ember" on magi (picked by hostname)
vim.g.mapleader = " "
vim.g.maplocalleader = " "

------------------------------------------------------------------
-- Options
------------------------------------------------------------------
local o = vim.opt
o.termguicolors  = true
o.number         = true
o.signcolumn     = "yes"
o.cursorline     = true
o.laststatus     = 3          -- one statusline across all splits
o.showmode       = false      -- lualine already shows the mode
o.scrolloff      = 8
o.splitright     = true
o.splitbelow     = true
o.updatetime     = 250
o.fillchars      = { eob = " " }

o.expandtab      = true       -- 4-space tabs
o.shiftwidth     = 4
o.tabstop        = 4
o.softtabstop    = 4

o.ignorecase     = true
o.smartcase      = true       -- ...unless the search has a capital letter
o.hlsearch       = false
o.incsearch      = true

------------------------------------------------------------------
-- Palette (same as the rest of the rice)
------------------------------------------------------------------
local neon = {
    rosewater = "#f5e0dc", flamingo = "#f2cdcd",
    pink      = "#f15bb5", mauve    = "#9b5de5",
    red       = "#ff6b81", maroon   = "#ff8fa3",
    peach     = "#ffb085", yellow   = "#ffc371",
    green     = "#81c784", teal     = "#5ccfe6",
    sky       = "#8be9fd", sapphire = "#74c7ec",
    blue      = "#8aa8ff", lavender = "#babbf1",
    text      = "#e0e0f0", subtext1 = "#c4c4e0", subtext0 = "#9d9dbf",
    overlay2  = "#8a8aab", overlay1 = "#76769a", overlay0 = "#6c6c8a",
    surface2  = "#3a3a5c", surface1 = "#2a2a45", surface0 = "#1a1a2f",
    base      = "#0f0f1e", mantle   = "#0b0b16", crust    = "#08080f",
}

-- magi's "ember": warm orange on near-black, same values as alacritty / eww / waybar there
local ember = {
    rosewater = "#f3e7dc", flamingo = "#f0c8b0",
    pink      = "#ffc857", mauve    = "#ff8c1a",
    red       = "#e5484d", maroon   = "#f06b6f",
    peach     = "#ffa94d", yellow   = "#f5a524",
    green     = "#a3d977", teal     = "#7fd1c7",
    sky       = "#9ee3da", sapphire = "#8fb3d9",
    blue      = "#e8b07a", lavender = "#f0c08a",
    text      = "#d8cbbf", subtext1 = "#c4b5a8", subtext0 = "#a8968a",
    overlay2  = "#8f7c6f", overlay1 = "#7a675a", overlay0 = "#66554a",
    surface2  = "#4a3a2e", surface1 = "#3a2c22", surface0 = "#241a14",
    base      = "#120d0a", mantle   = "#0e0a08", crust    = "#0a0705",
}
local on_magi = vim.uv.os_gethostname() == "magi"
local palette = on_magi and ember or neon

------------------------------------------------------------------
-- lazy.nvim bootstrap
------------------------------------------------------------------
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.uv.fs_stat(lazypath) then
    vim.fn.system({
        "git", "clone", "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git", "--branch=stable", lazypath,
    })
end
vim.opt.rtp:prepend(lazypath)
vim.opt.clipboard = "unnamedplus" -- share Neovim's clipboard with the system
vim.keymap.set("n", "<leader>r", 'ggVG"+p', { desc = "Replace whole file with clipboard" })

------------------------------------------------------------------
-- Plugins
------------------------------------------------------------------
require("lazy").setup({
    -- Colorscheme: Catppuccin Mocha re-tinted to the neon palette
    {
        "catppuccin/nvim",
        name = "catppuccin",
        lazy = false,
        priority = 1000,
        config = function()
            require("catppuccin").setup({
                flavour = "mocha",
                transparent_background = true, -- lets Alacritty's blur show through
                color_overrides = { mocha = palette },
                styles = {
                    comments  = { "italic" },
                    keywords  = { "bold" },
                    functions = { "bold" },
                },
                custom_highlights = function(c)
                    return {
                        CursorLine     = { bg = c.surface0 },
                        CursorLineNr   = { fg = c.pink, bold = true },
                        LineNr         = { fg = c.surface2 },
                        WinSeparator   = { fg = c.surface1 },
                        FloatBorder    = { fg = c.mauve },
                        NormalFloat    = { bg = c.mantle },
                        Pmenu          = { bg = c.mantle },
                        PmenuSel       = { bg = c.mauve, fg = c.crust, bold = true },
                        Visual         = { bg = on_magi and "#3a2c22" or "#3a2d5c" },
                        Search         = { bg = c.lavender, fg = c.crust },
                        IncSearch      = { bg = c.pink, fg = c.crust },
                        TelescopeBorder       = { fg = c.mauve },
                        TelescopePromptBorder = { fg = c.pink },
                        TelescopeTitle        = { fg = c.crust, bg = c.mauve, bold = true },
                        TelescopeSelection    = { bg = c.surface1, fg = c.text, bold = true },
                    }
                end,
                integrations = {
                    treesitter = true,
                    nvimtree   = true,
                    telescope  = { enabled = true },
                    cmp        = true,
                    gitsigns   = true,
                    mason      = true,
                    native_lsp = { enabled = true },
                },
            })
            vim.cmd.colorscheme("catppuccin")
        end,
    },

    -- Statusline: rounded "pill" sections like the bar & prompt
    {
        "nvim-lualine/lualine.nvim",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        opts = {
            options = {
                theme = "catppuccin",
                globalstatus = true,
                section_separators   = { left = "\u{e0b4}", right = "\u{e0b6}" },
                component_separators = "",
            },
            sections = {
                lualine_a = { { "mode", separator = { left = "\u{e0b6}" }, right_padding = 2 } },
                lualine_b = { "branch", "diff" },
                lualine_c = { { "filename", path = 1 }, "diagnostics" },
                lualine_x = { "filetype" },
                lualine_y = { "progress" },
                lualine_z = { { "location", separator = { right = "\u{e0b4}" }, left_padding = 2 } },
            },
        },
    },

    -- File explorer
    {
        "nvim-tree/nvim-tree.lua",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        config = function()
            require("nvim-tree").setup({
                view = { width = 30, side = "left" },
                filters = { dotfiles = false }, -- show hidden files
                renderer = {
                    root_folder_label = ":~:s?$?/..?",
                    indent_markers = { enable = true },
                    icons = {
                        glyphs = {
                            default = "",
                            symlink = "",
                            folder = {
                                default = "",
                                open = "",
                                empty = "",
                                empty_open = "",
                                symlink = "",
                            },
                            git = {
                                unstaged = "✗",
                                staged = "✓",
                                unmerged = "",
                                renamed = "➜",
                                untracked = "★",
                                deleted = "",
                                ignored = "◌",
                            },
                        },
                    },
                },
            })
        end,
    },

    -- Fuzzy finder (plenary is a hard requirement of telescope)
    {
        "nvim-telescope/telescope.nvim",
        dependencies = { "nvim-lua/plenary.nvim" },
        opts = {
            defaults = {
                prompt_prefix   = "  \u{f002}  ",
                selection_caret = " \u{276f} ",
                layout_config   = { prompt_position = "top" },
                sorting_strategy = "ascending",
            },
        },
    },

    -- Treesitter: pinned to master, the branch that still has
    -- require("nvim-treesitter.configs") (the default branch changed)
    {
        "nvim-treesitter/nvim-treesitter",
        branch = "master",
        build = ":TSUpdate",
        config = function()
            require("nvim-treesitter.configs").setup({
                ensure_installed = { "java", "lua", "python", "cpp", "c", "javascript", "html", "css" },
                highlight = { enable = true },
            })
        end,
    },

    -- Git signs in the gutter
    {
        "lewis6991/gitsigns.nvim",
        opts = {
            signs = {
                add          = { text = "\u{2503}" },
                change       = { text = "\u{2503}" },
                delete       = { text = "\u{2581}" },
                topdelete    = { text = "\u{2594}" },
                changedelete = { text = "\u{2503}" },
            },
        },
    },

    -- Editing helpers
    { "numToStr/Comment.nvim", opts = {} },
    { "windwp/nvim-autopairs", event = "InsertEnter", opts = {} },

    -- Discord rich presence (it had colorscheme options pasted in before)
    { "vyfor/cord.nvim", build = ":Cord update", opts = {} },

    -- LSP + completion
    { "neovim/nvim-lspconfig" },
    { "williamboman/mason.nvim", opts = { ui = { border = "rounded" } } },
    { "williamboman/mason-lspconfig.nvim" },
    { "hrsh7th/nvim-cmp" },
    { "hrsh7th/cmp-nvim-lsp" },
    { "L3MON4D3/LuaSnip" },
}, {
    ui = { border = "rounded" },
})

------------------------------------------------------------------
-- LSP
------------------------------------------------------------------
require("mason-lspconfig").setup()

local capabilities = require("cmp_nvim_lsp").default_capabilities()
local servers = {
    "pyright",   -- Python
    "ts_ls",     -- JS/React
    "clangd",    -- C/C++
    "jdtls",     -- Java
    "omnisharp", -- C#
    "phpactor",  -- PHP
    "html",      -- HTML
    "cssls",     -- CSS
    "lua_ls",    -- Lua
}
for _, server in ipairs(servers) do
    vim.lsp.config(server, { capabilities = capabilities })
    vim.lsp.enable(server)
end

vim.diagnostic.config({
    virtual_text = { prefix = "\u{25cf}" },
    severity_sort = true,
    float = { border = "rounded" },
    signs = {
        text = {
            [vim.diagnostic.severity.ERROR] = "\u{f057}",
            [vim.diagnostic.severity.WARN]  = "\u{f071}",
            [vim.diagnostic.severity.INFO]  = "\u{f05a}",
            [vim.diagnostic.severity.HINT]  = "\u{f0eb}",
        },
    },
})

------------------------------------------------------------------
-- Completion
------------------------------------------------------------------
local cmp = require("cmp")
local luasnip = require("luasnip")

cmp.setup({
    snippet = { expand = function(args) luasnip.lsp_expand(args.body) end },
    window = {
        completion    = cmp.config.window.bordered(),
        documentation = cmp.config.window.bordered(),
    },
    mapping = cmp.mapping.preset.insert({
        ["<C-n>"] = cmp.mapping.select_next_item(),
        ["<C-p>"] = cmp.mapping.select_prev_item(),
        ["<CR>"]  = cmp.mapping.confirm({ select = true }),
        ["<Tab>"] = cmp.mapping(function(fallback)
            if cmp.visible() then
                cmp.select_next_item()
            elseif luasnip.expand_or_jumpable() then
                luasnip.expand_or_jump()
            else
                fallback()
            end
        end, { "i", "s" }),
        ["<S-Tab>"] = cmp.mapping(function(fallback)
            if cmp.visible() then
                cmp.select_prev_item()
            elseif luasnip.jumpable(-1) then
                luasnip.jump(-1)
            else
                fallback()
            end
        end, { "i", "s" }),
    }),
    sources = cmp.config.sources({
        { name = "nvim_lsp" },
        { name = "luasnip" },
    }),
})

------------------------------------------------------------------
-- Keymaps
------------------------------------------------------------------
local map = vim.keymap.set
map("n", "<leader>e",  "<cmd>NvimTreeToggle<CR>",       { silent = true, desc = "File tree" })
map("n", "<leader>ff", "<cmd>Telescope find_files<CR>", { silent = true, desc = "Find files" })
map("n", "<leader>fg", "<cmd>Telescope live_grep<CR>",  { silent = true, desc = "Grep in project" })
map("n", "<leader>fb", "<cmd>Telescope buffers<CR>",    { silent = true, desc = "Open buffers" })
map("n", "gd", vim.lsp.buf.definition, { silent = true, desc = "Go to definition" })
map("i", "<C-BS>", "<C-W>", { silent = true, desc = "Delete word" })
