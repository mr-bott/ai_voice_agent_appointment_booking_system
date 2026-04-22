"""
Core tool implementations for the clinical agent.
Includes logic for doctor listing, availability checks, and appointment booking.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database.models import Appointment, AvailabilitySlot, Doctor, Patient


def _doctor_display_name(name: str) -> str:
    return name if name.lower().startswith("dr.") else f"Dr. {name}"


IST = timezone(timedelta(hours=5, minutes=30))

def _parse_requested_datetime(raw_value: str) -> datetime:
    value = (raw_value or "").strip()
    if not value:
        raise ValueError("No appointment time was provided.")

    formats = (
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            # Make it aware of IST
            parsed = parsed.replace(tzinfo=IST)
            if fmt == "%Y-%m-%d":
                return parsed.replace(hour=10, minute=0)
            return parsed
        except ValueError:
            continue

    raise ValueError(
        "Time format not recognized. Use formats like 2026-04-22 10:00 AM or 2026-04-22T10:00."
    )


async def ensure_demo_data(db: AsyncSession | None):
    """Initializes the database with sample doctors, availability slots, and a demo patient."""
    if db is None:
        return

    # Check if doctors exist
    doctor_names = ["Dr. Harry", "Dr. Smith", "Dr. Priya Raman", "Dr. Arun Kumar"]
    existing_doctors_res = await db.execute(select(Doctor).filter(Doctor.name.in_(doctor_names)))
    existing_doctors = {d.name: d for d in existing_doctors_res.scalars().all()}

    seeded_doctors = []
    for name in doctor_names:
        if name not in existing_doctors:
            specialty = "General Medicine"
            if "Harry" in name: specialty = "Pediatrics"
            elif "Smith" in name: specialty = "Cardiology"
            elif "Arun" in name: specialty = "Dermatology"
            
            doc = Doctor(name=name, specialty=specialty)
            db.add(doc)
            seeded_doctors.append(doc)
        else:
            seeded_doctors.append(existing_doctors[name])
    
    await db.flush()

    # Ensure slots for next 3 days
    now_ist = datetime.now(timezone.utc).astimezone(IST)
    base_date = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)

    for offset in range(4): # Today + 3 days
        day = base_date + timedelta(days=offset)
        for doctor in seeded_doctors:
            # Check if slots already exist for this doctor on this day
            day_start = day
            day_end = day + timedelta(days=1)
            existing_slots_res = await db.execute(
                select(AvailabilitySlot).filter(
                    and_(
                        AvailabilitySlot.doctor_id == doctor.id,
                        AvailabilitySlot.start_time >= day_start,
                        AvailabilitySlot.start_time < day_end
                    )
                )
            )
            if not existing_slots_res.scalars().first():
                # Create slots
                for hour in (9, 10, 11, 14, 15, 16):
                    start_time = day.replace(hour=hour, minute=0)
                    end_time = start_time + timedelta(minutes=30)
                    db.add(
                        AvailabilitySlot(
                            doctor_id=doctor.id,
                            start_time=start_time,
                            end_time=end_time,
                            is_booked=False,
                        )
                    )

    # Ensure demo patient
    patient_res = await db.execute(select(Patient).filter(Patient.phone_number == "+910000000001"))
    if not patient_res.scalars().first():
        patient = Patient(
            phone_number="+910000000001",
            name="Demo Patient",
            preferred_language="English",
        )
        db.add(patient)

    await db.commit()


async def get_default_patient_id(db: AsyncSession | None) -> int:
    if db is None:
        return 1

    await ensure_demo_data(db)
    result = await db.execute(select(Patient).order_by(Patient.id.asc()))
    patient = result.scalars().first()
    return patient.id if patient else 1


async def check_doctor_availability(db: AsyncSession | None, doctor_name: str, date: str) -> str:
    """Checks and returns available time slots for a specific doctor on a given date."""
    if db is None:
        return f"Dr. {doctor_name} is available on {date} at 10:00 AM and 2:00 PM."

    await ensure_demo_data(db)

    # Clean up common prefixes like "Dr.", "Doctor", etc.
    search_term = doctor_name.lower().replace("doctor ", "").replace("dr. ", "").replace("dr ", "").strip()
    result = await db.execute(select(Doctor).filter(Doctor.name.ilike(f"%{search_term}%")))
    doctor = result.scalars().first()
    if not doctor:
        return f"Doctor {doctor_name} not found."

    try:
        if date is None:
            return "Please provide the date in YYYY-MM-DD format."
        requested_day = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return "Please provide the date in YYYY-MM-DD format."

    slots_result = await db.execute(
        select(AvailabilitySlot)
        .filter(
            and_(
                AvailabilitySlot.doctor_id == doctor.id,
                AvailabilitySlot.is_booked.is_(False),
            )
        )
        .order_by(AvailabilitySlot.start_time.asc())
    )
    slots = [slot for slot in slots_result.scalars().all() if slot.start_time.date() == requested_day]

    if not slots:
        return f"{doctor.name} has no open slots on {date}. Please ask for another date."

    formatted_slots = ", ".join(slot.start_time.astimezone(IST).strftime("%I:%M %p") for slot in slots[:6])
    return f"{doctor.name} is available on {date} at {formatted_slots}."


async def list_doctors(db):
    """Retrieves all active doctors and their specialties from the database."""
    result = await db.execute(
        select(Doctor)
        .filter(Doctor.is_active == True)
        .order_by(Doctor.id.asc())
    )

    doctors = result.scalars().all()

    if not doctors:
        return "No doctors are currently available."

    lines = []

    for i, d in enumerate(doctors, start=1):
        lines.append(f"{i}. {d.name} - {d.specialty}")

    return (
        "Available doctors are: "
        + " ".join(lines)
        + " Which doctor would you like to book with?"
    )


async def book_appointment(
    db: AsyncSession | None,
    doctor_name: str,
    time_str: str,
    patient_name: str | None = None,
    phone_number: str | None = None,
) -> str:
    """
    Handles the end-to-end booking process.
    Resolves patient, doctor, and slot, then creates an appointment record.
    """
    try:
        requested_time = _parse_requested_datetime(time_str)
    except ValueError as e:
        return str(e)

    if db is None:
        p_name = patient_name or "Demo Patient"
        return (
            f"Appointment booked for {p_name} with {_doctor_display_name(doctor_name)} on "
            f"{requested_time.strftime('%Y-%m-%d at %I:%M %p')}."
        )

    await ensure_demo_data(db)

    # 1. Resolve Patient
    patient = None
    if phone_number:
        res = await db.execute(select(Patient).filter(Patient.phone_number == phone_number))
        patient = res.scalars().first()
        if not patient and patient_name:
            # Create new patient if phone not found but name provided
            patient = Patient(phone_number=phone_number, name=patient_name)
            db.add(patient)
            await db.flush()
    
    if not patient and patient_name:
        # Search by name if phone not provided or not found
        res = await db.execute(select(Patient).filter(Patient.name.ilike(f"%{patient_name}%")))
        patient = res.scalars().first()

    if not patient:
        # Fallback to Demo Patient
        res = await db.execute(select(Patient).filter(Patient.phone_number == "+910000000001"))
        patient = res.scalars().first()
        if not patient:
            return "Could not find a valid patient record for booking."

    # 2. Resolve Doctor
    search_term = doctor_name.lower().replace("doctor ", "").replace("dr. ", "").replace("dr ", "").strip()
    doctor_result = await db.execute(select(Doctor).filter(Doctor.name.ilike(f"%{search_term}%")))
    doctor = doctor_result.scalars().first()
    if not doctor:
        return f"Could not book the appointment because doctor {doctor_name} was not found."

    # 3. Resolve Slot
    slot_result = await db.execute(
        select(AvailabilitySlot)
        .filter(
            and_(
                AvailabilitySlot.doctor_id == doctor.id,
                AvailabilitySlot.start_time == requested_time,
                AvailabilitySlot.is_booked.is_(False),
            )
        )
    )
    slot = slot_result.scalars().first()

    if not slot:
        alternatives_result = await db.execute(
            select(AvailabilitySlot)
            .filter(
                and_(
                    AvailabilitySlot.doctor_id == doctor.id,
                    AvailabilitySlot.is_booked.is_(False),
                    AvailabilitySlot.start_time >= (datetime.now(IST) - timedelta(hours=1))
                )
            )
            .order_by(AvailabilitySlot.start_time.asc())
        )
        alternatives = alternatives_result.scalars().all()[:3]
        if not alternatives:
            return f"{doctor.name} does not have any free slots right now."

        formatted = ", ".join(item.start_time.astimezone(IST).strftime("%I:%M %p on %Y-%m-%d") for item in alternatives)
        return f"I couldn't find a slot at that exact time. Available times for {doctor.name} are: {formatted}. Would you like to pick one of these?"

    # 4. Create Appointment
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        reason="Voice Agent Booking",
        status="scheduled",
    )
    slot.is_booked = True
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    
    print(f"DEBUG: Successfully committed appointment ID {appointment.id} for patient {patient.name} ({patient.id})")

    return (
        f"Appointment booked successfully for {patient.name} with {doctor.name} on "
        f"{slot.start_time.astimezone(IST).strftime('%Y-%m-%d at %I:%M %p')}."
    )


async def cancel_appointment(db: AsyncSession | None, appointment_id: int) -> str:
    if db is None:
        return f"Appointment {appointment_id} cancelled."

    result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
    appointment = result.scalars().first()
    if not appointment:
        return "Appointment not found."

    appointment.status = "cancelled"
    slot_result = await db.execute(
        select(AvailabilitySlot).filter(
            and_(
                AvailabilitySlot.doctor_id == appointment.doctor_id,
                AvailabilitySlot.start_time == appointment.start_time,
            )
        )
    )
    slot = slot_result.scalars().first()
    if slot:
        slot.is_booked = False
    await db.commit()
    return "Appointment successfully cancelled."


async def list_patient_appointments(db: AsyncSession | None, patient_name: str | None = None, phone_number: str | None = None) -> str:
    """List all appointments for a specific patient."""
    if db is None:
        return "You have one appointment with Dr. Smith on 2026-04-22."

    # Resolve Patient
    patient = None
    if phone_number:
        res = await db.execute(select(Patient).filter(Patient.phone_number == phone_number))
        patient = res.scalars().first()
    
    if not patient and patient_name:
        res = await db.execute(select(Patient).filter(Patient.name.ilike(f"%{patient_name}%")))
        patient = res.scalars().first()

    if not patient:
        return "I couldn't find your records. Please provide your name or phone number."

    result = await db.execute(
        select(Appointment, Doctor)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .filter(Appointment.patient_id == patient.id)
        .order_by(Appointment.start_time.desc())
    )
    rows = result.all()
    
    if not rows:
        return f"No appointments found for {patient.name}."
    
    apps = []
    for app, doc in rows:
        time_str = app.start_time.astimezone(IST).strftime("%Y-%m-%d at %I:%M %p")
        apps.append(f"- {doc.name} on {time_str} ({app.status})")
    
    return f"Appointments for {patient.name}:\n" + "\n".join(apps)


async def find_patient(db: AsyncSession | None, name: str) -> str:
    """Find a patient in the database by name."""
    if db is None:
        return "Patient Murali found (ID: 1)."

    if not name or name.lower() in ["your name", "full name", "your full name", "customer name", "placeholder"]:
        return "ERROR: You are attempting to search with a placeholder. You MUST ask the user for their actual name before calling this tool."

    res = await db.execute(select(Patient).filter(Patient.name.ilike(f"%{name}%")))

    patient = res.scalars().first()

    if patient:
        return f"Found patient: {patient.name} (Phone: {patient.phone_number}, ID: {patient.id}). You can now proceed with the booking for this patient."
    else:
        return f"No patient found with the name '{name}'. You should ask the user if they would like to register as a new patient."


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_doctors",
            "description": "List all doctors and their specialties.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
    "type": "function",
    "function": {
        "name": "reschedule_appointment",
        "description": "Reschedule an existing appointment using booking ID and new preferred date.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "integer",
                    "description": "Existing booking ID"
                },
                "new_date": {
                    "type": "string",
                    "description": "New date in YYYY-MM-DD format"
                }
            },
            "required": ["appointment_id", "new_date"]
        },
    },
},  
    {
        "type": "function",
        "function": {
            "name": "check_doctor_availability",
            "description": "Check if a specific doctor is available on a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {
                        "type": "string",
                        "description": "The doctor name, for example Dr. Smith",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                    },
                },
                "required": ["doctor_name", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book a clinical appointment after the user confirms a specific doctor and exact date/time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Doctor name"},
                    "time_str": {
                        "type": "string",
                        "description": "Exact appointment date/time like 2026-04-22 10:00 AM",
                    },
                    "patient_name": {
                        "type": "string", 
                        "description": "Optional: Full name of the patient"
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "Optional: Patient's phone number"
                    }
                },
                "required": ["doctor_name", "time_str"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "integer",
                        "description": "The unique ID of the appointment to cancel."
                    }
                },
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_patient",
            "description": "Search for a patient by name to verify their identity before booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Full name of the patient"}
                },
                "required": ["name"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "list_appointments",
            "description": "List all appointments for a patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "Patient name"},
                    "phone_number": {"type": "string", "description": "Patient phone number"}
                },
                "required": [],
            },
        },
    },
]

