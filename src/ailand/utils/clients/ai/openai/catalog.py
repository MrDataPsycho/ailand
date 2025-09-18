from enum import StrEnum


class ChatModelSelection(StrEnum):
    GPT4_1_MINI = "gpt-4.1-mini"
    GPT_4o_MINI = "gpt-4o-mini"
    DEFAULT = GPT4_1_MINI


class EmbeddingModelSelection(StrEnum):
    EMBEDDING_3_LARGE = "text-embedding-3-large"
    DEFAULT = EMBEDDING_3_LARGE


class APIVersion(StrEnum):
    V_2024_08_01 = "2024-08-01-preview"
    DEFAULT = V_2024_08_01


