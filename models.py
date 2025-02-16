from pydantic import BaseModel, ValidationError, Field
from enum import Enum
from typing import Optional, List

# Pydantic models for data validation
class Address(BaseModel):
    address_name: Optional[str] = Field(
        None,
        title="Name of the address",
        description="An example would be the name of the company located at that point.",
    )
    street: str
    city: Optional[str] = None
    province: str
    postal_code: str


class Contact(BaseModel):
    contact_person: Optional[str] = None
    phone: Optional[str] = None


class ActivityEnum(str, Enum):
    Collection = "Collection"
    Delivery = "Delivery"


class ColorEnum(str, Enum):
    Unknown = "Unknown"
    Black = "Black"
    White = "White"
    Grey = "Grey"
    Blue = "Blue"
    Red = "Red"
    Yellow = "Yellow"
    Green = "Green"
    Brown = "Brown"


class Vehicle(BaseModel):
    license_plate: str
    vin: Optional[str] = Field(
        None,
        title="Vehicle Identification Number (VIN)",
        description="The unique identifier for a specific vehicle.",
    )
    make: str
    model: Optional[str] = Field(
        None,
        title="Vehicle Model",
        description="Model of the vehicle. In case of containing the make referenced in the model, replace it to leave the model only",
    )
    color: Optional[ColorEnum] = Field(
        None,
        title="Vehicle color",
        description="In case of not being specified, or just find a dot . , leave it empty.",
    )
    release_id: Optional[str] = Field(
        None,
        title="Release ID",
        description="Unique identifier for the vehicle, often used in tracking or management systems. "
        "Must follow the format of a mix of alphanumeric characters, e.g., '004A0724359VT002024'.",
        example="004A0724359VT002024",
    )
    weight: Optional[float] = None
    volume: Optional[float] = None
    activity: Optional[ActivityEnum] = None

class StopInfo(BaseModel):
    stop_number: int
    address: Address
    contact: Optional[Contact] = None
    vehicles: List[Vehicle]
    comments: Optional[str] = None

class Header(BaseModel):
    company_name: Optional[str] = None
    customer_code: Optional[str] = Field(
        None,
        title="ID de ubicación",
        description="Code, usually G3060 or G3622 for the company.",
        example="G3060",
    )
    shipment_id: str
    available_at: str = Field(
        None,
        title="Fecha de creación de la orden",
        description="Date when the order is created.",
        example="31/12/2022",
    )
    delivery_requested_at: str = Field(
        None,
        title="Fecha compromiso de entrega o fecha de inicio de la orden",
        description="Date when the order should be completed by.",
        example="31/12/2022",
    )
    sender_email: Optional[str] = None
    number_of_stops: int
    number_of_vehicles: int

class Order(BaseModel):
    header: Header
    stops: List[StopInfo]


class OrderList(BaseModel):
    orders: List[Order]