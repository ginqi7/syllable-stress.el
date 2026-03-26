;;; syllable-stress.el ---                               -*- lexical-binding: t; -*-

;; Copyright (C) 2025  Qiqi Jin

;; Author: Qiqi Jin <ginqi7@gmail.com>
;; Keywords:

;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation, either version 3 of the License, or
;; (at your option) any later version.

;; This program is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with this program.  If not, see <https://www.gnu.org/licenses/>.

;;; Commentary:

;;

;;; Code:

(require 'websocket-bridge)

(defvar syllable-stress-py-path
  (concat (file-name-directory (or load-file-name (buffer-file-name))) "syllable-stress.py")
  "Stores the path to the syllable-stress.py file by concatenating the directory of the current file with \"syllable-stress.py\".")

;;; Custom variables
(defcustom syllable-stress-python (executable-find "python3")
  "The Python interpreter."
  :type 'string)

(defcustom syllable-stress-minimum-syllables 3
  ""
  :type 'int)

(setq syllable-stress-python "uv run")

;;; Internal Variables

(defvar syllable-stress--ovs nil)

;;; Commands

(defun syllable-stress-start ()
  "Start syllable-stress."
  (interactive)
  (websocket-bridge-server-start)
  (websocket-bridge-app-start
   "syllable-stress"
   syllable-stress-python
   syllable-stress-py-path))

(defun syllable-stress-stop ()
  "Stop syllable-stress."
  (interactive)
  (websocket-bridge-app-exit "syllable-stress"))

(defun syllable-stress-restart ()
  "Restart syllable-stress."
  (interactive)
  (syllable-stress-stop)
  (syllable-stress-start)
  (split-window-below -10)
  (other-window 1)
  (websocket-bridge-app-open-buffer "syllable-stress"))

(defun syllable-stress--name (symbol)
  (substring (symbol-name symbol) 1))

(defun syllable-stress-render-word (&rest args)
  (let* ((syllable-stress (car args))
         (word (syllable-stress--name (car syllable-stress)))
         (beg)
         (end)
         (ov))
    (save-excursion
      (goto-char (window-start))
      (while (re-search-forward (concat "\\b" (regexp-quote word) "\\b") (window-end) t)
        (setq beg (- (point) (length word)))
        (dolist (syllable (nth 1 syllable-stress))
          (setq end (+ beg (car syllable)))
          (pcase (nth 1 syllable)
            (1 (setq ov (make-overlay beg end)) (overlay-put ov 'face 'error) (push ov syllable-stress--ovs))
            (2 (setq ov (make-overlay beg end)) (overlay-put ov 'face 'warn) (push ov syllable-stress--ovs)))
          (setq beg end))))))

(defun syllable-stress-render-string (str)
  ""
  (interactive)
  (websocket-bridge-call "syllable-stress" "render-string" str))

(defun syllable-stress-render-window ()
  ""
  (interactive)
  (syllable-stress-clear-ovs)
  (syllable-stress-render-string (buffer-substring-no-properties (window-start) (window-end))))

(defun syllable-stress-clear-ovs ()
  (interactive)
  (dolist (ov syllable-stress--ovs)
    (when (overlayp ov)
      (delete-overlay ov)))
  (setq syllable-stress--ovs nil))

(provide 'syllable-stress)
;;; syllable-stress.el ends here
