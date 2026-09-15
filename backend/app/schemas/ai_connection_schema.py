from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AiConnectionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    provider: Literal["openai", "gemini"]
    model: str = Field(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    api_key: str | None = Field(default=None, max_length=4096)
    is_default: bool = False


class AiModelListRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    provider: Literal["openai", "gemini"]
    api_key: str | None = Field(default=None, max_length=4096)
    connection_id: str | None = None
