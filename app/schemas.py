from pydantic import BaseModel

class PlayerCreate(BaseModel):
    name: str

class StatUpgrade(BaseModel):
    stat_name: str

class AbilityLearn(BaseModel):
    ability_name: str

class EquipItem(BaseModel):
    item_name: str
    slot: str