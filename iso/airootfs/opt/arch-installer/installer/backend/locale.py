"""
installer/backend/locale.py
----------------------------
Backend functions for Stage 3 — Locale.

Reads the list of available locales from /etc/locale.gen (the standard
Arch source), parses them, and provides the list to the UI.

The actual write (uncommenting lines in /etc/locale.gen and running
locale-gen) happens later during the chroot phase of installation.
"""

import logging
import os

log = logging.getLogger(__name__)

# Path on the live ISO and on the installed system
_LOCALE_GEN_PATH = "/etc/locale.gen"

# Fallback list if the file can't be read (e.g. during development on
# a non-Arch system where /etc/locale.gen doesn't exist)
_FALLBACK_LOCALES = [
    "en_US.UTF-8 UTF-8",
    "en_GB.UTF-8 UTF-8",
    "de_DE.UTF-8 UTF-8",
    "fr_FR.UTF-8 UTF-8",
    "es_ES.UTF-8 UTF-8",
    "it_IT.UTF-8 UTF-8",
    "pt_BR.UTF-8 UTF-8",
    "pt_PT.UTF-8 UTF-8",
    "ru_RU.UTF-8 UTF-8",
    "pl_PL.UTF-8 UTF-8",
    "nl_NL.UTF-8 UTF-8",
    "sv_SE.UTF-8 UTF-8",
    "nb_NO.UTF-8 UTF-8",
    "da_DK.UTF-8 UTF-8",
    "fi_FI.UTF-8 UTF-8",
    "zh_CN.UTF-8 UTF-8",
    "zh_TW.UTF-8 UTF-8",
    "ja_JP.UTF-8 UTF-8",
    "ko_KR.UTF-8 UTF-8",
    "ar_SA.UTF-8 UTF-8",
    "tr_TR.UTF-8 UTF-8",
    "cs_CZ.UTF-8 UTF-8",
    "hu_HU.UTF-8 UTF-8",
    "ro_RO.UTF-8 UTF-8",
    "uk_UA.UTF-8 UTF-8",
]


def list_locales(utf8_only: bool = False) -> list:
    """
    Return a sorted list of available locale strings, e.g. ['en_US.UTF-8', ...].

    Reads /etc/locale.gen and returns every locale listed there (both
    commented-out and already-enabled lines), because on a fresh Arch ISO
    all lines are commented out by default.

    utf8_only: if True, only return locales containing 'UTF-8'.
               Used for Beginner mode to reduce noise.
    """
    locales = []

    if os.path.exists(_LOCALE_GEN_PATH):
        try:
            with open(_LOCALE_GEN_PATH, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    # Strip leading '#' and whitespace — all entries are
                    # commented out by default on a fresh Arch install
                    stripped = line.lstrip("#").strip()

                    # Skip blank lines and lines that don't look like locales
                    # A locale line looks like: "en_US.UTF-8 UTF-8"
                    if not stripped or " " not in stripped:
                        continue

                    # The locale identifier is the first word on the line
                    locale_id = stripped.split()[0]

                    # Basic sanity check — locale IDs contain an underscore
                    if "_" not in locale_id:
                        continue

                    if utf8_only and "UTF-8" not in locale_id:
                        continue

                    locales.append(locale_id)

            if locales:
                return sorted(set(locales))  # set() removes any duplicates

        except OSError as e:
            log.warning("Could not read %s: %s", _LOCALE_GEN_PATH, e)

    # Fall back to the built-in list
    log.info("Using built-in locale list (locale.gen not available)")
    result = []
    for entry in _FALLBACK_LOCALES:
        locale_id = entry.split()[0]
        if utf8_only and "UTF-8" not in locale_id:
            continue
        result.append(locale_id)
    return sorted(result)


def locale_to_lang(locale: str) -> str:
    """
    Derive the LANG= value from a locale string.
    For most locales this is the same thing, e.g. 'en_US.UTF-8' → 'en_US.UTF-8'.
    We keep this as a separate function so future logic (e.g. special cases)
    can live here without touching the UI.
    """
    return locale
