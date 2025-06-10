# extraction.py

import os
import time
from threading import Event
from typing import Optional, Tuple

from translation import Translator

TAGS = ['[GÉNÉRAL]', '[T]', '[AT]', '[ALL]', '[CT]']


def follow_log(path: str, stop_event: Event):
    """Générateur qui lit en continu les nouvelles lignes d'un fichier de log."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            while not stop_event.is_set():
                line = f.readline()
                if line:
                    yield line.strip()
                else:
                    time.sleep(0.5)  # Je mets ici une pause de 0.5s de façon arbitraire dans le but de ne pas faire trop tourner la boucle
    except FileNotFoundError:
        yield f"ERROR_FILENOTFOUND:{path}"


def is_player_chat(line: str) -> bool:
    """Vérifie si la ligne contient un message de chat de joueur."""
    return any(tag in line for tag in TAGS) and "\xa0" in line


def extract_player_and_message(chat_line: str) -> Optional[Tuple[str, str]]:
    """Extrait le nom du joueur et le message d'une ligne de chat."""
    chat_line = chat_line.replace('\u200e', '')
    try:
        _, content_after_tag = chat_line.split(']', 1)
        content_after_tag = content_after_tag.strip()
        player_name_part, player_message = content_after_tag.split('\xa0: ', 1)
        player_name = player_name_part.split('﹫')[0].replace('[MORT(E)]', '').replace('[DEAD]', '').strip()
        return player_name, player_message.strip()
    except (ValueError, IndexError):
        return None


def process_log_line(line: str, translator: Translator) -> Optional[Tuple[str, str, bool, Optional[str], bool, bool]]:
    """Traite une seule ligne du log en utilisant une instance de Translator existante."""
    if not is_player_chat(line):
        return None

    extracted = extract_player_and_message(line)
    if not extracted:
        return None

    player_name, message = extracted

    final_text, was_translated, original_lang, from_cache = translator.translate_message(message)

    is_error = final_text.startswith("[ERROR]")
    if is_error:
        player_name = "ERREUR"

    return player_name, final_text, was_translated, original_lang, is_error, from_cache
