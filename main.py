# main.py

import json
import os
import threading
from queue import Empty, Queue
from tkinter import filedialog, messagebox
from typing import List, Optional

import customtkinter

# Autrs modules
from extraction import follow_log, process_log_line
from translation import Translator

# --- CONSTANTES DE STYLE ---
FONT_TITLE = ("Arial", 24, "bold")
FONT_LABEL = ("Arial", 12)
FONT_LABEL_BOLD = ("Arial", 12, "bold")
FONT_INFO = ("Arial", 12, "italic")
FONT_CONFIG_LABEL = ("Arial", 14)

COLOR_GREEN_NORMAL = "#38573F"
COLOR_GREEN_HOVER = "#547D54"
COLOR_RED_NORMAL = "#84181C"
COLOR_RED_HOVER = "#B13026"
COLOR_PLAYER_NAME = "cyan"
COLOR_ERROR = "red"
COLOR_INFO_TEXT = "gray60"
COLOR_BUTTON_GENERIC = "gray30"
COLOR_BUTTON_GENERIC_HOVER = "gray20"
COLOR_BANNED_WORD_SELECTED = "#2B2B2B"

# --- CONSTANTES DE CONFIGURATION ---
DEFAULT_CS_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive"
DEFAULT_TRANSLATOR = "Google Translator"


class ConfigPanel(customtkinter.CTkScrollableFrame):
    """Panneau latéral de configuration de l'application."""

    def __init__(self, master: customtkinter.CTk) -> None:
        """Initialise le panneau de configuration."""
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)

        self.banned_words: List[str] = []
        self.selected_label: Optional[customtkinter.CTkLabel] = None
        self.config_path: Optional[str] = None
        self.cs_path: str = DEFAULT_CS_PATH

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Crée et positionne tous les widgets du panneau."""
        self._create_config_file_section()
        self._create_language_section()
        self._create_tokens_section()
        self._create_translator_section()
        self._create_banned_words_section()
        self._create_cs_path_section()
        self._create_save_section()

    def _create_config_file_section(self) -> None:
        """Crée la section pour charger un fichier de configuration."""
        self.btn_select_config = customtkinter.CTkButton(
            self, text="Charger un fichier de config", command=self.load_config_file, width=180
        )
        self.btn_select_config.grid(row=0, column=0, pady=(10, 5))

        self.label_config_path = customtkinter.CTkLabel(
            self, text="Pas de fichier trouvé", font=FONT_CONFIG_LABEL, wraplength=180, anchor="w"
        )
        self.label_config_path.grid(row=1, column=0, pady=(0, 10), padx=5, sticky="ew")

    def _create_language_section(self) -> None:
        """Crée la section pour les options de langue."""
        self.chk_en = customtkinter.CTkCheckBox(self, text="Exclure la traduction de l'anglais")
        self.chk_en.grid(row=3, column=0, sticky="w", padx=10, pady=(0, 10))

    def _create_tokens_section(self) -> None:
        """Crée la section pour les tokens d'API."""
        customtkinter.CTkLabel(self, text="Token DeepL :").grid(row=4, column=0, sticky="w", padx=10)
        self.token_deepl = customtkinter.CTkEntry(self, show="*")
        self.token_deepl.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")

        customtkinter.CTkLabel(self, text="Token Gemini :").grid(row=6, column=0, sticky="w", padx=10)
        self.token_google_gemini = customtkinter.CTkEntry(self, show="*")
        self.token_google_gemini.grid(row=7, column=0, padx=10, pady=(0, 15), sticky="ew")

        self.token_deepl.bind("<KeyRelease>", self.update_translators)
        self.token_google_gemini.bind("<KeyRelease>", self.update_translators)

    def _create_translator_section(self) -> None:
        """Crée la section pour sélectionner le traducteur."""
        self.translator_var = customtkinter.StringVar(value=DEFAULT_TRANSLATOR)
        self.translator_menu = customtkinter.CTkComboBox(
            self, values=[DEFAULT_TRANSLATOR], variable=self.translator_var
        )
        self.translator_menu.grid(row=8, column=0, padx=10, pady=(0, 15))

    def _create_banned_words_section(self) -> None:
        """Crée la section pour gérer les mots à ne pas traduire."""
        customtkinter.CTkLabel(self, text="Mots dont la traduction est à éviter (moins d'appels API)").grid(row=9, column=0, sticky="w", padx=10)

        words_container = customtkinter.CTkFrame(self)
        words_container.grid(row=10, column=0, padx=10, sticky="ew")
        words_container.grid_columnconfigure(0, weight=1)

        self.scroll_frame = customtkinter.CTkScrollableFrame(words_container, height=150)
        self.scroll_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        entry_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        entry_frame.grid(row=11, column=0, pady=5, padx=10)

        self.entry_banned_word = customtkinter.CTkEntry(entry_frame, width=120, placeholder_text="mot")
        self.entry_banned_word.grid(row=0, column=0, padx=(0, 5))
        self.entry_banned_word.bind("<Return>", lambda event: self.add_banned_word())

        self.btn_add_word = customtkinter.CTkButton(
            entry_frame, text="+", width=30, command=self.add_banned_word
        )
        self.btn_add_word.grid(row=0, column=1, padx=(0, 2))

        self.btn_remove_word = customtkinter.CTkButton(
            entry_frame, text="-", width=30, command=self.remove_banned_word
        )
        self.btn_remove_word.grid(row=0, column=2)

    def _create_cs_path_section(self) -> None:
        """Crée la section pour le chemin du jeu."""
        self.btn_select_cs = customtkinter.CTkButton(
            self, text="Choisir le dossier Counter-Strike", command=self.select_cs_folder, width=180
        )
        self.btn_select_cs.grid(row=12, column=0, padx=5, pady=(15, 5))

        self.label_cs_path = customtkinter.CTkLabel(self, text=self.cs_path, font=FONT_CONFIG_LABEL, wraplength=180)
        self.label_cs_path.grid(row=13, column=0, padx=5, pady=(0, 10), sticky="we")

    def _create_save_section(self) -> None:
        """Crée le bouton de sauvegarde de la configuration."""
        self.btn_save = customtkinter.CTkButton(
            self, text="Enregistrer la config", command=self.save_config, width=180
        )
        self.btn_save.grid(row=14, column=0, padx=5, pady=(0, 15))

    def set_enabled(self, enabled: bool) -> None:
        """Active ou désactive tous les widgets interactifs du panneau."""
        state = "normal" if enabled else "disabled"

        self.btn_select_config.configure(state=state)
        self.chk_en.configure(state=state)
        self.token_deepl.configure(state=state)
        self.token_google_gemini.configure(state=state)
        self.translator_menu.configure(state=state)
        self.btn_select_cs.configure(state=state)
        self.btn_save.configure(state=state)
        self.entry_banned_word.configure(state=state)
        self.btn_add_word.configure(state=state)
        self.btn_remove_word.configure(state=state)

    def get_config_data(self) -> dict:
        """Retourne un dictionnaire avec la configuration actuelle."""
        return {
            "exclude_english": bool(self.chk_en.get()),
            "token_deepl": self.token_deepl.get().strip(),
            "token_google_gemini": self.token_google_gemini.get().strip(),
            "translator": self.translator_var.get(),
            "banned_words": self.banned_words.copy(),
            "cs_path": self.cs_path
        }

    def add_banned_word(self) -> None:
        """Ajoute un mot entré à la liste des mots bannis."""
        word = self.entry_banned_word.get().strip()
        if word and word not in self.banned_words:
            self.banned_words.append(word)
            self.display_banned_words()
            self.entry_banned_word.delete(0, "end")

    def remove_banned_word(self) -> None:
        """Supprime le mot actuellement sélectionné de la liste."""
        if self.selected_label:
            word = self.selected_label.cget("text")
            if word in self.banned_words:
                self.banned_words.remove(word)
                self.display_banned_words()
                self.selected_label = None

    def display_banned_words(self) -> None:
        """Rafraîchit l'affichage de la liste des mots bannis."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        for i, word in enumerate(self.banned_words):
            label = customtkinter.CTkLabel(self.scroll_frame, text=word, anchor="w", cursor="hand2")
            label.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            label.bind("<Button-1>", lambda event, lbl=label: self.select_label(lbl))

    def select_label(self, label: customtkinter.CTkLabel) -> None:
        """Met en surbrillance un mot banni lors du clic."""
        if self.selected_label:
            self.selected_label.configure(fg_color="transparent")
        label.configure(fg_color=COLOR_BANNED_WORD_SELECTED)
        self.selected_label = label

    def update_translators(self, event=None) -> None:
        """Met à jour la liste des traducteurs disponibles en fonction des tokens."""
        options = [DEFAULT_TRANSLATOR]
        if self.token_deepl.get().strip():
            options.append("DeepL")
        if self.token_google_gemini.get().strip():
            options.append("Gemini")

        current = self.translator_var.get()
        self.translator_menu.configure(values=options)
        if current not in options:
            self.translator_var.set(DEFAULT_TRANSLATOR)

    def load_config_file(self) -> None:
        """Ouvre une boîte de dialogue pour charger un fichier de configuration JSON."""
        path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not (path and os.path.exists(path)):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            self.load_config_data(config_data)
            self.config_path = path
            self.label_config_path.configure(text=f"Loaded: {os.path.basename(path)}")
            messagebox.showinfo("Success", "Configuration loaded successfully.")
        except (json.JSONDecodeError, IOError) as e:
            messagebox.showerror("Error", f"Error loading config file: {e}")

    def load_config_data(self, config_data: dict) -> None:
        """Charge les données d'un dictionnaire dans les widgets de configuration."""
        action = self.chk_en.select if config_data.get("exclude_english") else self.chk_en.deselect
        action()

        def set_entry_text(widget, text):
            widget.delete(0, "end")
            widget.insert(0, text)

        set_entry_text(self.token_deepl, config_data.get("token_deepl", ""))
        set_entry_text(self.token_google_gemini, config_data.get("token_google_gemini", ""))

        self.translator_var.set(config_data.get("translator", DEFAULT_TRANSLATOR))
        self.banned_words = config_data.get("banned_words", []).copy()
        self.display_banned_words()
        self.cs_path = config_data.get("cs_path", DEFAULT_CS_PATH)
        self.label_cs_path.configure(text=self.cs_path)
        self.update_translators()

    def select_cs_folder(self) -> None:
        """Ouvre une boîte de dialogue pour sélectionner le dossier du jeu."""
        folder = filedialog.askdirectory(title="Choose CS folder", initialdir=self.cs_path)
        if folder:
            self.cs_path = folder
            self.label_cs_path.configure(text=folder)

    def save_config(self) -> None:
        """Sauvegarde la configuration actuelle dans un fichier JSON."""
        path = self.config_path
        if not path:
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
            if not path:
                return
            self.config_path = path
            self.label_config_path.configure(text=f"Config: {os.path.basename(path)}")

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.get_config_data(), f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Success", "Configuration saved successfully.")
        except IOError as e:
            messagebox.showerror("Error", f"Error saving configuration: {e}")


class App(customtkinter.CTk):
    """Classe principale de l'application CS Translator."""

    def __init__(self) -> None:
        """Initialise l'application."""
        super().__init__()
        customtkinter.set_appearance_mode("dark")

        self.title("CS Translator")
        self.geometry("1000x900")

        self.is_playing: bool = False
        self.message_queue: Queue = Queue()
        self.stop_listening: threading.Event = threading.Event()
        self.listening_thread: Optional[threading.Thread] = None

        self._setup_ui()
        self._check_message_queue()

    def _setup_ui(self) -> None:
        """Configure la grille et crée tous les widgets de l'interface."""
        self.grid_columnconfigure(0, weight=7)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_chat_section()
        self._create_config_panel()

    def _create_header(self) -> None:
        """Crée l'en-tête de l'application avec le titre et le bouton play/stop."""
        top_frame = customtkinter.CTkFrame(self)
        top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(top_frame, text="CS Translator", font=FONT_TITLE).grid(row=0, column=0, pady=(10, 5))

        self.play_button = customtkinter.CTkButton(
            top_frame, text="Débuter l'écoute", command=self.toggle_play,
            fg_color=COLOR_GREEN_NORMAL, hover_color=COLOR_GREEN_HOVER
        )
        self.play_button.grid(row=1, column=0, pady=(0, 10))

    def _create_chat_section(self) -> None:
        """Crée la zone de chat et le bouton pour l'effacer."""
        self.chat_frame = customtkinter.CTkScrollableFrame(self)
        self.chat_frame.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="nsew")

        customtkinter.CTkButton(
            self, text="Effacer l'historique", command=self.clear_chat,
            fg_color=COLOR_BUTTON_GENERIC, hover_color=COLOR_BUTTON_GENERIC_HOVER
        ).grid(row=2, column=0, padx=10, pady=10, sticky="ew")

    def _create_config_panel(self) -> None:
        """Instancie et positionne le panneau de configuration."""
        self.config_panel = ConfigPanel(self)
        self.config_panel.grid(row=1, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")

    def toggle_play(self) -> None:
        """Bascule l'état d'écoute (marche/arrêt)."""
        if self.is_playing:
            self.stop_listening_process()
        else:
            self.start_listening()

    def start_listening(self) -> None:
        """Démarre le processus d'écoute dans un thread séparé."""
        self.is_playing = True
        self.stop_listening.clear()
        self.play_button.configure(text="Stopper l'écoute", fg_color=COLOR_RED_NORMAL, hover_color=COLOR_RED_HOVER)
        self.config_panel.set_enabled(False)

        config = self.config_panel.get_config_data()
        self.listening_thread = threading.Thread(target=self._listening_worker, args=(config,), daemon=True)
        self.listening_thread.start()

    def stop_listening_process(self) -> None:
        """Arrête le processus d'écoute."""
        self.is_playing = False
        self.stop_listening.set()
        self.play_button.configure(text="Débuter l'écoute", fg_color=COLOR_GREEN_NORMAL, hover_color=COLOR_GREEN_HOVER)
        self.config_panel.set_enabled(True)

    def _listening_worker(self, config: dict) -> None:
        """Worker exécuté en arrière-plan pour lire et traiter le fichier de log."""
        log_path = os.path.join(config["cs_path"], "game", "csgo", "console.log")

        translator = Translator(config) # On fait l'instance du traducteur ici pour qu'il garde le cache en mémoire

        try:
            for line in follow_log(log_path, self.stop_listening):
                if line.startswith("ERROR_FILENOTFOUND:"):
                    path = line.split(":", 1)[1]
                    self.message_queue.put(("ERREUR", f"Log file not found: {path}", False, None, True))
                    break

                processed_data = process_log_line(line, translator)
                if processed_data:
                    self.message_queue.put(processed_data)

        except Exception as e:
            print(f"An unexpected error occurred in the listening worker: {e}")
            self.message_queue.put(("ERREUR", f"Unexpected error: {e}", False, None, True))
        finally:
            self.after(0, self.stop_listening_process)

    def _check_message_queue(self) -> None:
        """Vérifie la queue de messages et met à jour l'UI."""
        try:
            for _ in range(10):  # Traiter max 10 messages par cycle pour ne pas bloquer l'UI (en cas de vague de spam)
                data_tuple = self.message_queue.get_nowait()
                self.add_chat_message(*data_tuple)
        except Empty:
            pass
        finally:
            self.after(100, self._check_message_queue)

    def add_chat_message(self, player_name: str, message: str, was_translated: bool, original_lang: Optional[str], is_error: bool, from_cache: bool) -> None:
        """Ajoute un message formaté dans la zone de chat."""
        msg_frame = customtkinter.CTkFrame(self.chat_frame, corner_radius=8)
        msg_frame.grid(sticky="ew", pady=5, padx=5)
        msg_frame.grid_columnconfigure(0, weight=1)

        display_name = "[ERREUR]" if is_error else player_name
        next_row = 0

        customtkinter.CTkLabel(
            msg_frame, text=display_name, font=FONT_LABEL_BOLD, text_color=COLOR_ERROR if is_error else COLOR_PLAYER_NAME
        ).grid(row=next_row, column=0, sticky="w", padx=10, pady=(5, 0))
        next_row += 1

        if was_translated:
            translator = self.config_panel.translator_var.get()
            # On vérifie la premiere lettre pour savoir si c'est une voyelle, dans quel cas on ajoute "l'" au lieu de "le"
            if original_lang:
                if original_lang.lower().startswith(("a", "e", "i", "o", "u", "y")):
                    original_lang = f"l'{original_lang}"
                else:
                    original_lang = f"le {original_lang}"

                lang_info = f" (Depuis {original_lang})"
            else:
                lang_info = ""

            trad_text = f"Traduit par {translator}{lang_info}"
            # On remplace par la mention du cache si nécessaire
            if from_cache:
                trad_text = " (Depuis le cache)"

            customtkinter.CTkLabel(
                msg_frame, text=trad_text, font=FONT_INFO, text_color=COLOR_INFO_TEXT, justify="left"
            ).grid(row=next_row, column=0, sticky="w", padx=10, pady=(0, 5))
            next_row += 1

        customtkinter.CTkLabel(
            msg_frame, text=message, font=FONT_LABEL, wraplength=self.chat_frame.winfo_width() - 50, justify="left"
        ).grid(row=next_row, column=0, sticky="w", padx=10, pady=(0, 5))

        self.after(10, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Scrolle la zone de chat tout en bas."""
        self.chat_frame._parent_canvas.update_idletasks()
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def clear_chat(self) -> None:
        """Efface tous les messages de la zone de chat."""
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self.chat_frame._parent_canvas.yview_moveto(0.0)

    def on_closing(self) -> None:
        """Gère la fermeture propre de l'application."""
        if self.is_playing:
            self.stop_listening_process()
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=1.0)
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
