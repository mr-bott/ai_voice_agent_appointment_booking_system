"""
ToolRouter maps LLM function calls to their respective backend implementations.
It handles argument parsing and executes the appropriate tool logic.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from .tools import book_appointment, check_doctor_availability, cancel_appointment, get_default_patient_id, list_doctors, list_patient_appointments, find_patient
import json

class ToolRouter:
    def __init__(self, db: AsyncSession | None):
        self.db = db

    async def execute_tool(self, tool_call, patient_id: int | None = None):
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments or "{}")
        resolved_patient_id = patient_id or await get_default_patient_id(self.db)
        
        if func_name == "list_doctors":
            return await list_doctors(self.db)

        if func_name == "check_doctor_availability":

            return await check_doctor_availability(
                self.db, 
                args.get("doctor_name"), 
                args.get("date")
            )
            
        elif func_name == "book_appointment":
            return await book_appointment(
                self.db, 
                args.get("doctor_name"), 
                args.get("time_str"),
                patient_name=args.get("patient_name"),
                phone_number=args.get("phone_number")
            )

            
        elif func_name == "cancel_appointment":
            return await cancel_appointment(
                self.db,
                args.get("appointment_id")
            )
            
        elif func_name == "list_appointments":
            return await list_patient_appointments(
                self.db,
                patient_name=args.get("patient_name"),
                phone_number=args.get("phone_number")
            )

        elif func_name == "find_patient":
            return await find_patient(
                self.db,
                name=args.get("name")
            )

            
        return f"Tool {func_name} is not implemented."
