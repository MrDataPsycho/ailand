from enum import StrEnum


class ChatModelSelection(StrEnum):
    GPT4_1_MINI = "gpt-4.1-mini"
    GPT_4o_MINI = "gpt-4o-mini"


class EmbeddingModelSelection(StrEnum):
    EMBEDDING_3_LARGE = "text-embedding-3-large"


class APIVersion(StrEnum):
    LATEST = "2024-08-01-preview"
    V_2024_08_01 = "2024-08-01-preview"


