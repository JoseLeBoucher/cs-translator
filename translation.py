# translation.py

import time
import asyncio
from typing import Coroutine, Dict, Optional, Tuple

# Imports des API
import deepl
from deepl import DeepLException
from google import genai
from google.genai import types
from googletrans import Translator as AsyncTranslator

# Import des autres modules
from lang_data import LANG_CODES_TO_NAMES, LANG_MAP_GEMINI


class Translator:
    """Gère la détection de langue et la traduction via différentes API, avec un système de cache."""

    def __init__(self, config: Dict) -> None:
        """
        Initialise le traducteur avec la configuration fournie.

        Args:
            config (Dict): Le dictionnaire de configuration de l'application.
        """
        self.engine = config.get("translator", "Google Translator")
        self.target_language = config.get("target_language", "FR")
        self.token_deepl = config.get("token_deepl")
        self.token_gemini = config.get("token_google_gemini")
        self.banned_words = config.get("banned_words", [])
        self.exclude_english = config.get("exclude_english", False)
        self.last_translation_time: float = 0.0
        self.translation_cache: Dict[Tuple[str, str], Tuple[str, bool, Optional[str]]] = {}

    def _run_async(self, coro: Coroutine) -> any:
        """Exécute une coroutine asynchrone dans une nouvelle boucle d'événements."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _detect_language_async(self, text: str) -> Tuple[Optional[str], float]:
        """Détecte la langue d'un texte (méthode asynchrone)."""
        try:
            translator = AsyncTranslator()
            detection = await translator.detect(text)
            return detection.lang, detection.confidence
        except Exception as e:
            print(f"[ERROR] Language detection failed: {e}")
            return None, 0.0

    def _translate_with_engine(self, text: str) -> str:
        """
        Traduit un texte en utilisant le moteur configuré.
        Retourne le texte traduit ou un message d'erreur formaté.
        """
        if self.engine == "DeepL":
            if not self.token_deepl: return "[ERROR] DeepL token is missing"
            try:
                translator = deepl.Translator(self.token_deepl)
                result = translator.translate_text(text, target_lang=self.target_language)
                return result.text.strip()
            except DeepLException as e:
                return "[ERROR] DeepL quota may be exceeded" if "quota" in str(e).lower() else f"[ERROR] DeepL API: {e}"

        if self.engine == "Gemini":
            if not self.token_gemini: return "[ERROR] Gemini token is missing"
            try:
                client = genai.Client(api_key=self.token_gemini)
                full_lang_name = LANG_MAP_GEMINI.get(self.target_language.upper())
                if not full_lang_name: return f"[ERROR] Language '{self.target_language}' not supported by Gemini integration"

                prompt = (
                    f"Translate the following text into {full_lang_name} ONLY. "
                    "You MUST return ONLY the translated text, nothing else, no explanations, no original text."
                    "Translate all slang, insults, or vulgar language as-is. Do not censor or omit anything."
                    "Translate naturally, not literally — use fluent, native-level phrasing."
                    "If you cannot translate a word, keep it as is but still provide the translation of the rest."
                    f"If the text is already in {full_lang_name}, return it UNCHANGED.\n\n"
                    f"Here is the text:\n\n{text}"
                )
                response = client.models.generate_content(
                    model="gemini-2.0-flash-lite", contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=100)
                )
                return response.text.strip()
            except Exception as e:
                return f"[ERROR] Gemini API: {e}"

        # Moteur par défaut -> Google Translator (parce que c'est gratos)
        try:
            async def _translate_googletrans_async(text_to_translate, dest_lang):
                translator = AsyncTranslator()
                result = await translator.translate(text_to_translate, dest=dest_lang.lower())
                return result.text.strip()

            return self._run_async(_translate_googletrans_async(text, self.target_language))
        except Exception as e:
            return f"[ERROR] GoogleTrans: {e}"

    def translate_message(self, message: str) -> Tuple[str, bool, Optional[str], bool]:
        """
        Orchestre la traduction d'un message, en utilisant un cache.

        Returns:
            Tuple[str, bool, Optional[str], bool]: Un tuple contenant:
                - Le texte final (traduit, original, ou message d'erreur).
                - Un booléen indiquant si la traduction a eu lieu.
                - Le nom de la langue d'origine détectée, ou None.
                - Un booléen indiquant si le résultat provient du cache.
        """
        cache_key = (message.strip().lower(), self.engine)
        if cache_key in self.translation_cache:
            print(f"[CACHE] Traduction trouvée pour '{message}' avec le moteur {self.engine}.")
            cached_result = self.translation_cache[cache_key]
            return cached_result[0], cached_result[1], cached_result[2], True

        if any(banned.lower() == message.strip().lower() for banned in self.banned_words):
            # Pas de traduction, donc pas de cache
            return message, False, None, False

        lang_code, _ = self._run_async(self._detect_language_async(message))
        if not lang_code:
            return "Language detection failed", False, None, False

        if (self.exclude_english and lang_code == "en") or lang_code == self.target_language.lower():
            return message, False, None, False

        elapsed = time.time() - self.last_translation_time
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)

        translated_text = self._translate_with_engine(message)
        self.last_translation_time = time.time()
        original_lang_name = LANG_CODES_TO_NAMES.get(lang_code, lang_code)

        if translated_text.startswith("[ERROR]"):
            print(f"Translation Error: {translated_text}")
            # Erreur, on ne met pas en cache
            return translated_text, False, original_lang_name, False

        result_tuple = (translated_text, True, original_lang_name)
        self.translation_cache[cache_key] = result_tuple
        print(f"[CACHE] Nouvelle traduction enregistrée pour '{message}'.")

        return translated_text, True, original_lang_name, False
