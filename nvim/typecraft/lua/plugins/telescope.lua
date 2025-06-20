return {
  {
    "nvim-telescope/telescope-ui-select.nvim",
  },
  {
    "nvim-telescope/telescope.nvim",
    tag = "0.1.6",
    dependencies = { "nvim-lua/plenary.nvim" },
    config = function()
      require("telescope").setup({
        extensions = {
          ["ui-select"] = {
            require("telescope.themes").get_dropdown({}),
          },
        },
        pickers = {
          find_files = {
            hidden = true,
          },
        },
      })
      local builtin = require("telescope.builtin")
      vim.keymap.set("n", "<leader>ff", builtin.find_files, {})
      vim.keymap.set("n", "<leader>fg", builtin.live_grep, {})
      vim.keymap.set("n", "<leader>gf", builtin.git_files, { desc = "Telescope Git files" })
      vim.keymap.set("n", "<leader>gs", builtin.git_status, { desc = "Telescope Git status" })
      vim.keymap.set("n", "<leader>gc", builtin.git_commits, { desc = "Telescope Git commits" })
      vim.keymap.set("n", "<leader>gb", builtin.git_branches, { desc = "Telescope Git branchs" })
      vim.keymap.set("n", "<leader>bb", builtin.buffers, { desc = "Telescope Buffers" })
      vim.keymap.set("n", "<leader>hh", builtin.help_tags, { desc = "Telescope Help" })

      require("telescope").load_extension("ui-select")
    end,
  },
}
