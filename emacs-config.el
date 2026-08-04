(add-to-list 'custom-theme-load-path "~/.emacs.d/themes")
(load-theme 'github-dark-vscode)

(setq-default python-indent-offset 4)
(add-hook 'python-mode-hook
  (lambda ()
    (setq indent-tabs-mode t
          tab-width 4
          python-indent-offset 4)))
