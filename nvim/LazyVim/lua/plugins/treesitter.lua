return {
  {
    "nvim-treesitter/nvim-treesitter",
    opts = {
      ensure_installed = {
        "bash",
        "vim",
        "vimdoc",
        "lua",
        "javascript",
        "json",
        "html",
        "yaml",
        "php",
        "phpdoc",
      },
      highlight = { enable = true },
      indent = { enable = true },
    },
  },
}
