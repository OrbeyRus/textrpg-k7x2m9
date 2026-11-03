from pydantic import BaseModel


class PlayerCreate(BaseModel):
    name: str = ""
    user_token: str = ""


class NameUpdate(BaseModel):
    name: str


class NewGameRequest(BaseModel):
    user_token: str = ""


class StatUpgrade(BaseModel):
    stat_name: str


class AbilityLearn(BaseModel):
    ability_name: str


class EquipItem(BaseModel):
    item_name: str
    slot: str
