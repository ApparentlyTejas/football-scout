from pydantic import BaseModel, ConfigDict


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    nationality: str | None
    primary_position: str | None
