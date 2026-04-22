"""
REST API endpoints for managing patients, doctors, and appointments.
This module provides standard CRUD operations via FastAPI.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from . import schemas
from ..database.models import Patient, Doctor, Appointment, AvailabilitySlot
from ..database.connection import get_db

router = APIRouter()

import traceback

@router.post("/patients/", response_model=schemas.PatientResponse)
async def create_patient(patient: schemas.PatientCreate, db: AsyncSession = Depends(get_db)):
    patient_data = patient.model_dump() if hasattr(patient, "model_dump") else patient.dict()

    new_patient = Patient(**patient_data)
    db.add(new_patient)

    try:
        await db.commit()
        await db.refresh(new_patient)
        return new_patient

    except Exception as e:
        await db.rollback()
        print("REAL ERROR:", str(e))
        traceback.print_exc()

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.get("/patients/", response_model=List[schemas.PatientResponse])
async def get_patients(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/patients/{patient_id}", response_model=schemas.PatientResponse)
async def get_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).filter(Patient.id == patient_id))
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# --- Doctors ---
@router.post("/doctors/", response_model=schemas.DoctorResponse)
async def create_doctor(doctor: schemas.DoctorCreate, db: AsyncSession = Depends(get_db)):
    doctor_data = doctor.model_dump() if hasattr(doctor, "model_dump") else doctor.dict()
    new_doctor = Doctor(**doctor_data)
    db.add(new_doctor)
    await db.commit()
    await db.refresh(new_doctor)
    return new_doctor


@router.get("/doctors/", response_model=List[schemas.DoctorResponse])
async def get_doctors(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/doctors/{doctor_id}", response_model=schemas.DoctorResponse)
async def get_doctor(doctor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor).filter(Doctor.id == doctor_id))
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


# --- Appointments ---
@router.post("/appointments/", response_model=schemas.AppointmentResponse)
async def create_appointment(appointment: schemas.AppointmentCreate, db: AsyncSession = Depends(get_db)):
    appointment_data = appointment.model_dump() if hasattr(appointment, "model_dump") else appointment.dict()
    new_appointment = Appointment(**appointment_data)
    db.add(new_appointment)
    await db.commit()
    await db.refresh(new_appointment)
    return new_appointment

@router.get("/appointments/", response_model=List[schemas.AppointmentResponse])
async def get_appointments(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appointment).offset(skip).limit(limit))
    return result.scalars().all()

@router.put("/appointments/{appointment_id}/status", response_model=schemas.AppointmentResponse)
async def update_appointment_status(appointment_id: int, status_update: schemas.AppointmentUpdateStatus, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
    appointment = result.scalars().first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appointment.status = status_update.status
    await db.commit()
    await db.refresh(appointment)
    return appointment


# --- Availability Slots ---
@router.post("/availability/", response_model=schemas.AvailabilitySlotResponse)
async def create_availability_slot(slot: schemas.AvailabilitySlotCreate, db: AsyncSession = Depends(get_db)):
    slot_data = slot.model_dump() if hasattr(slot, "model_dump") else slot.dict()
    new_slot = AvailabilitySlot(**slot_data)
    db.add(new_slot)
    await db.commit()
    await db.refresh(new_slot)
    return new_slot

@router.get("/availability/", response_model=List[schemas.AvailabilitySlotResponse])
async def get_availability(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AvailabilitySlot).offset(skip).limit(limit))
    return result.scalars().all()
