"""
Data models for Pokemon TCG cards and sets.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Attack(BaseModel):
    """Model for Pokemon card attacks."""
    
    name: str
    cost: List[str] = Field(default_factory=list)
    converted_energy_cost: int = 0
    damage: str = ""
    text: str = ""


class Ability(BaseModel):
    """Model for Pokemon card abilities."""
    
    name: str
    text: str
    type: str = "Ability"


class Weakness(BaseModel):
    """Model for Pokemon card weakness."""
    
    type: str
    value: str


class Resistance(BaseModel):
    """Model for Pokemon card resistance."""
    
    type: str
    value: str


class CardImage(BaseModel):
    """Model for card images."""
    
    small: str
    large: str


class CardPrice(BaseModel):
    """Model for card market prices."""
    
    low: Optional[float] = None
    mid: Optional[float] = None
    high: Optional[float] = None
    market: Optional[float] = None
    direct_low: Optional[float] = None


class Legalities(BaseModel):
    """Model for set legalities in different formats."""
    
    unlimited: Optional[str] = None
    standard: Optional[str] = None
    expanded: Optional[str] = None


class SetImage(BaseModel):
    """Model for set images."""
    
    symbol: str
    logo: str

class Set(BaseModel):
    """Model for Pokemon TCG sets."""
    
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)
    
    id: str
    name: str
    series: str
    printedTotal: int
    total: int
    legalities: Optional[Legalities] = None
    ptcgo_code: Optional[str] = Field(None, alias="ptcgoCode")
    release_date: str = Field(alias="releaseDate")
    updated_at: str = Field(alias="updatedAt")
    images: Optional[SetImage] = None
    
    @property
    def release_datetime(self) -> datetime:
        """Get release date as datetime object."""
        return datetime.strptime(self.release_date, "%Y/%m/%d")
    
    @property
    def symbol_url(self) -> Optional[str]:
        """Get the set symbol URL if available."""
        return self.images.symbol if self.images else None
    
    @property
    def logo_url(self) -> Optional[str]:
        """Get the set logo URL if available."""
        return self.images.logo if self.images else None


class Card(BaseModel):
    """Model for Pokemon TCG cards."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str
    name: str
    supertype: str
    subtypes: List[str] = Field(default_factory=list)
    hp: Optional[str] = None
    types: List[str] = Field(default_factory=list)
    evolves_from: Optional[str] = None
    evolves_to: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    attacks: List[Attack] = Field(default_factory=list)
    abilities: List[Ability] = Field(default_factory=list)
    weaknesses: List[Weakness] = Field(default_factory=list)
    resistances: List[Resistance] = Field(default_factory=list)
    retreat_cost: List[str] = Field(default_factory=list)
    converted_retreat_cost: Optional[int] = None
    set: Set
    number: str
    artist: Optional[str] = None
    rarity: Optional[str] = None
    flavor_text: Optional[str] = None
    national_pokedex_numbers: List[int] = Field(default_factory=list)
    images: Optional[CardImage] = None
    tcgplayer: Optional[Dict[str, Any]] = None
    cardmarket: Optional[Dict[str, Any]] = None
    
    @property
    def full_name(self) -> str:
        """Get full card name including set and number."""
        return f"{self.name} ({self.set.id} {self.number})"
    
    @property
    def image_url(self) -> Optional[str]:
        """Get the large image URL if available."""
        return self.images.large if self.images else None
    
    @property
    def small_image_url(self) -> Optional[str]:
        """Get the small image URL if available."""
        return self.images.small if self.images else None


class SearchResult(BaseModel):
    """Model for API search results."""
    
    data: List[Any]
    page: int = 1
    page_size: int = 250
    count: int = 0
    total_count: int = 0