from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..database.models import Patient, Appointment, MemoryLog

class PersistentMemory:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_patient_profile(self, phone_number: str):
        result = await self.db.execute(select(Patient).filter(Patient.phone_number == phone_number))
        return result.scalars().first()

    async def create_patient_profile(self, phone_number: str, name: str = None, preferred_language: str = "English"):
        patient = Patient(phone_number=phone_number, name=name, preferred_language=preferred_language)
        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)
        return patient

    async def update_patient_language(self, patient_id: int, language: str):
        result = await self.db.execute(select(Patient).filter(Patient.id == patient_id))
        patient = result.scalars().first()
        if patient:
            patient.preferred_language = language
            await self.db.commit()

    async def log_interaction(self, patient_id: int, session_id: str, interaction_type: str, content: str):
        log = MemoryLog(
            patient_id=patient_id,
            session_id=session_id,
            interaction_type=interaction_type,
            content=content
        )
        self.db.add(log)
        await self.db.commit()

    async def get_patient_appointments(self, patient_id: int):
        result = await self.db.execute(
            select(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.start_time.desc())
        )
        return result.scalars().all()
