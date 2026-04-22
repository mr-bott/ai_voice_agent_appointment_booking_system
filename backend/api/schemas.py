from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Patient Schemas
class PatientBase(BaseModel):
    phone_number: str
    name: Optional[str] = None
    preferred_language: Optional[str] = "English"

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Doctor Schemas
class DoctorBase(BaseModel):
    name: str
    specialty: str
    is_active: Optional[bool] = True

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: int

    class Config:
        from_attributes = True

# Appointment Schemas
class AppointmentBase(BaseModel):
    patient_id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdateStatus(BaseModel):
    status: str

class AppointmentResponse(AppointmentBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# AvailabilitySlot Schemas
class AvailabilitySlotBase(BaseModel):
    doctor_id: int
    start_time: datetime
    end_time: datetime
    is_booked: Optional[bool] = False

class AvailabilitySlotCreate(AvailabilitySlotBase):
    pass

class AvailabilitySlotResponse(AvailabilitySlotBase):
    id: int

    class Config:
        from_attributes = True
