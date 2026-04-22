/**
 * PatientList component: Fetches and displays a list of registered patients from the backend.
 * Provides a quick view of the patient database.
 */
"use client";

import React, { useEffect, useState } from 'react';
import { Search, User } from 'lucide-react';

interface Patient {
  id: number;
  name: string;
  phone_number: string;
}

export default function PatientList() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPatients = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/patients/');
      if (res.ok) {
        const data = await res.json();
        setPatients(data);
      }
    } catch (error) {
      // Ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
    // Increase interval to 30 seconds as patient data changes less frequently
    const interval = setInterval(fetchPatients, 30000);
    return () => clearInterval(interval);
  }, []);


  return (
    <div className="bg-slate-900/40 border border-slate-800/60 rounded-3xl p-6 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-white">Registered Patients</h3>
      </div>

      <div className="space-y-3">
        {loading ? (
          <p className="text-xs text-slate-500">Syncing database...</p>
        ) : patients.length === 0 ? (
          <p className="text-xs text-slate-500">No registered patients found.</p>
        ) : (
          patients.map((patient) => (
            <div key={patient.id} className="p-4 bg-slate-800/20 rounded-2xl border border-slate-700/20">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center text-slate-300">
                  <User size={18} />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-100">{patient.name || `Patient #${patient.id}`}</p>
                  <p className="text-[10px] font-medium text-slate-500">{patient.phone_number}</p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
