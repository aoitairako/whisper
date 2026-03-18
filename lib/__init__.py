"""Whisper transcription library — Single Source of Truth."""

from .core import (
    batch as batch,
)
from .core import (
    get_local_status as get_local_status,
)
from .core import (
    process_voice_memos as process_voice_memos,
)
from .core import (
    transcribe as transcribe,
)
from .dictionary import (
    apply_dictionary as apply_dictionary,
)
from .dictionary import (
    apply_dictionary_to_result as apply_dictionary_to_result,
)
from .dictionary import (
    dictionary_add as dictionary_add,
)
from .dictionary import (
    dictionary_list as dictionary_list,
)
from .dictionary import (
    load_dictionaries as load_dictionaries,
)
from .formats import to_srt as to_srt
from .formats import to_vtt as to_vtt
from .vocabulary import (
    get_vocab_dirs as get_vocab_dirs,
)
from .vocabulary import (
    load_vocabulary as load_vocabulary,
)
from .vocabulary import (
    vocabulary_add as vocabulary_add,
)
from .vocabulary import (
    vocabulary_list as vocabulary_list,
)

__all__ = [
    "transcribe",
    "batch",
    "process_voice_memos",
    "get_local_status",
    "load_vocabulary",
    "vocabulary_list",
    "vocabulary_add",
    "get_vocab_dirs",
    "load_dictionaries",
    "apply_dictionary",
    "apply_dictionary_to_result",
    "dictionary_list",
    "dictionary_add",
    "to_srt",
    "to_vtt",
]
