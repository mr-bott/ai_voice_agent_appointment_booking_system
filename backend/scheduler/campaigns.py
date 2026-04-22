import asyncio
from .celery_app import celery_app
from ..database.connection import AsyncSessionLocal
from ..database.models import CampaignJob, Patient
from sqlalchemy.future import select

@celery_app.task(name="process_outbound_campaign")
def process_outbound_campaign(job_id: int):
    """
    Background task to initiate an outbound call.
    In a real system, this would trigger a Twilio/Plivo API call 
    which would connect to our WebSocket endpoint.
    """
    # Celery is synchronous by default, so we wrap async DB calls
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_execute_outbound(job_id))
    return f"Processed job {job_id}"

async def _execute_outbound(job_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CampaignJob).filter(CampaignJob.id == job_id))
        job = result.scalars().first()
        
        if not job:
            return
            
        patient_result = await session.execute(select(Patient).filter(Patient.id == job.patient_id))
        patient = patient_result.scalars().first()
        
        print(f"Initiating outbound call to {patient.phone_number} for {job.campaign_type}")
        
        # Here we would use an external provider API to dial out.
        # e.g., twilio_client.calls.create(to=patient.phone_number, url="https://ourdomain.com/twiml")
        
        job.status = "completed"
        await session.commit()
