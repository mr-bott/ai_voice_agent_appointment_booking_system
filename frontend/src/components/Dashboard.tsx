/**
 * Dashboard component: The main container for the Clinical Voice AI interface.
 * Displays the voice assistant, booking history, and handles real-time data synchronization.
 */
"use client";

import React, { useEffect, useState, useRef, useCallback } from 'react';
import VoiceInterface from './VoiceInterface';
import { Calendar, Activity } from 'lucide-react';

interface Appointment {
  id: number;
  patient_id: number;
  doctor_id: number;
  start_time: string;
  status: string;
  doctor?: {
    name: string;
  };
}

export default function Dashboard() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const bookingScrollRef = useRef<HTMLDivElement>(null);

  const fetchAppointments = useCallback(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/appointments/');
      if (!res.ok) return;
      const data = await res.json();

      if (!Array.isArray(data)) {
        setAppointments([]);
        return;
      }

      // Slice the last 8 appointments FIRST to reduce API calls
      const recentData = data.slice(-8).reverse();

      const detailedAppointments = await Promise.all(recentData.map(async (app: any) => {
        try {
          // Fetch doctor info
          const docRes = await fetch(`http://127.0.0.1:8000/api/doctors/${app.doctor_id}`);
          const docData = docRes.ok ? await docRes.json() : null;

          // Fetch patient info
          const patRes = await fetch(`http://127.0.0.1:8000/api/patients/${app.patient_id}`);
          const patData = patRes.ok ? await patRes.json() : null;

          return {
            ...app,
            doctor: docData,
            patient: patData
          };
        } catch {
          return app;
        }
      }));

      setAppointments(detailedAppointments);
    } catch (error) {
      // Quietly fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAppointments();
    // Increase interval to 15 seconds to reduce server load
    const interval = setInterval(fetchAppointments, 15000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll booking history to top (latest)
  useEffect(() => {
    if (bookingScrollRef.current) {
      bookingScrollRef.current.scrollTop = 0;
    }
  }, [appointments]);


  return (
    <div className="h-screen bg-[#0a0c10] text-slate-200 p-2 md:p-4 selection:bg-indigo-500/30 flex flex-col overflow-hidden">
      <div className="max-w-7xl mx-auto w-full flex flex-col h-full space-y-4">

        <header className="flex justify-between items-center shrink-0 px-2 py-2">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Activity size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-white leading-none">
                HealthSync AI
              </h1>
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Live Ops</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-black text-indigo-400 bg-indigo-400/10 px-2 py-1 rounded-md uppercase tracking-wider">System Active</span>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1 min-h-0 pb-2">
          <div className="lg:col-span-2 h-full min-h-0">
            <div className="bg-slate-900/20 border border-slate-800/40 rounded-3xl overflow-hidden shadow-2xl h-full">
              <VoiceInterface onBookingSuccess={fetchAppointments} />
            </div>
          </div>

          <div className="h-full flex flex-col min-h-0">
            <div className="bg-slate-900/40 border border-slate-800/60 rounded-3xl p-5 shadow-xl backdrop-blur-md flex flex-col h-full overflow-hidden">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Calendar size={20} className="text-indigo-400" /> Booking History
                </h3>
                <span className="text-xs font-bold text-indigo-400 bg-indigo-400/10 px-2 py-1 rounded-md uppercase tracking-wider">Live</span>
              </div>

              <div 
                ref={bookingScrollRef}
                className="space-y-4 flex-1 overflow-y-auto pr-2 scrollbar-hide scroll-smooth"
              >
                {loading ? (
                  <div className="text-center py-10"><p className="text-slate-500 text-sm">Syncing...</p></div>
                ) : appointments.length === 0 ? (
                  <div className="text-center py-10">
                    <p className="text-slate-500 text-sm">No recent activity.</p>
                  </div>
                ) : (
                  appointments.map((app: any) => {
                    const start = new Date(app.start_time);
                    const end = new Date(app.end_time);
                    const diffMins = Math.round((end.getTime() - start.getTime()) / 60000);
                    const durationText = diffMins >= 60 
                      ? `${Math.floor(diffMins/60)}h ${diffMins%60 > 0 ? (diffMins%60) + 'm' : ''}` 
                      : `${diffMins} mins`;

                    return (
                      <div key={app.id} className="group p-4 bg-slate-800/30 rounded-2xl border border-slate-700/30 transition-all duration-300 hover:bg-slate-800/50 hover:border-indigo-500/30 shadow-lg">
                        <div className="flex items-start justify-between gap-4">
                          <div className="space-y-1.5 flex-1">
                            <div className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em] mb-1 opacity-80">
                              Booking #{app.id}
                            </div>
                            <h4 className="text-sm font-black text-white leading-tight">
                              {app.doctor?.name || 'Dr. Smith'}
                            </h4>
                            <p className="text-xs font-medium text-slate-400 pt-1">
                              Patient: <span className="text-slate-100 font-bold">{app.patient?.name || `ID #${app.patient_id}`}</span>
                            </p>
                            <div className="inline-flex items-center mt-2 px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-[9px] font-black uppercase tracking-tighter">
                              {durationText} Slot
                            </div>
                          </div>
                          
                          <div className="text-right flex flex-col items-end">
                            <div className="text-xl font-black text-white leading-none tracking-tighter">
                              {start.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                            </div>
                            <div className="text-xs font-bold text-indigo-400 mt-2 uppercase tracking-tight">
                              {start.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}
                            </div>
                            <div className="mt-3 text-[8px] font-black text-slate-600 uppercase tracking-widest">
                              {app.status}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })


                )}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
