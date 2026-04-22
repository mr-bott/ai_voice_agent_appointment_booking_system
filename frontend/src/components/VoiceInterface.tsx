/**
 * VoiceInterface component: Manages the bidirectional WebSocket communication for voice AI.
 * Handles microphone input, audio downsampling, and real-time transcription display.
 */
"use client";

import React, { useState, useEffect, useRef } from "react";
import AICore from "./AICore";

type ConnectionState = "standby" | "connecting" | "active" | "error";

interface Message {
  role: "user" | "assistant" | "system";
  text: string;
  isFinal: boolean;
  timestamp: number;
}

const TARGET_SAMPLE_RATE = 16000;

interface VoiceInterfaceProps {
  onBookingSuccess?: () => void;
}

export default function VoiceInterface({ onBookingSuccess }: VoiceInterfaceProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>("standby");
  const [messages, setMessages] = useState<Message[]>([]);
  const [statusMessage, setStatusMessage] = useState("Tap to start conversation");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [volume, setVolume] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  const mediaStream = useRef<MediaStream | null>(null);
  const inputAudioContext = useRef<AudioContext | null>(null);
  const analyser = useRef<AnalyserNode | null>(null);
  const animationFrame = useRef<number | null>(null);
  const currentPlayback = useRef<HTMLAudioElement | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const updateVolume = (analyserNode: AnalyserNode) => {
    const dataArray = new Uint8Array(analyserNode.frequencyBinCount);
    analyserNode.getByteFrequencyData(dataArray);
    const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
    
    // Sensitivity and Noise Floor
    const sensitivity = 2.5;
    const noiseFloor = 35; // Higher threshold to filter out all background noise
    
    let value = 0;
    if (average > noiseFloor) {
      value = Math.min(1, ((average - noiseFloor) / (128 - noiseFloor)) * sensitivity);
    } else {
      value = 0; // Absolute zero for anything below floor
    }
    
    setVolume(value);
    animationFrame.current = requestAnimationFrame(() => updateVolume(analyserNode));
  };

  const cleanupResources = () => {
    if (animationFrame.current) cancelAnimationFrame(animationFrame.current);
    if (mediaStream.current) {
      mediaStream.current.getTracks().forEach(track => track.stop());
      mediaStream.current = null;
    }
    if (inputAudioContext.current) {
      inputAudioContext.current.close().catch(console.error);
      inputAudioContext.current = null;
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    if (currentPlayback.current) {
      currentPlayback.current.pause();
      currentPlayback.current = null;
    }
  };

  useEffect(() => {
    return () => cleanupResources();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const upsertMessage = (role: Message["role"], text: string, isFinal: boolean) => {
    setMessages((prev) => {
      if (!isFinal && prev.length > 0 && prev[prev.length - 1].role === role && !prev[prev.length - 1].isFinal) {
        return [...prev.slice(0, -1), { role, text, isFinal, timestamp: Date.now() }];
      }
      if (isFinal && prev.length > 0 && prev[prev.length - 1].role === role && !prev[prev.length - 1].isFinal) {
        return [...prev.slice(0, -1), { role, text, isFinal: true, timestamp: Date.now() }];
      }
      return [...prev, { role, text, isFinal, timestamp: Date.now() }];
    });
  };

  const startAudioStreaming = (stream: MediaStream) => {
    const context = new AudioContext();
    inputAudioContext.current = context;
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    
    const analyzerNode = context.createAnalyser();
    analyzerNode.fftSize = 256;
    analyser.current = analyzerNode;
    source.connect(analyzerNode);
    updateVolume(analyzerNode);

    processor.onaudioprocess = (event) => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
      const channelData = event.inputBuffer.getChannelData(0);
      const downsampled = downsampleBuffer(channelData, context.sampleRate, TARGET_SAMPLE_RATE);
      const pcmBuffer = float32ToInt16Buffer(downsampled);
      ws.current.send(pcmBuffer);
    };

    source.connect(processor);
    processor.connect(context.destination);
  };

  const startRecording = async () => {
    try {
      setErrorMessage("");
      setConnectionState("connecting");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStream.current = stream;

      const wsUrl = `ws://127.0.0.1:8000/ws/audio`;
      ws.current = new WebSocket(wsUrl);
      ws.current.binaryType = "arraybuffer";

      ws.current.onopen = () => {
        setIsRecording(true);
        setConnectionState("active");
        setStatusMessage("Agent is listening...");
        startAudioStreaming(stream);
      };

      ws.current.onmessage = async (event) => {
        if (typeof event.data === "string") {
          const msg = JSON.parse(event.data);
          if (msg.type === "transcript") {
            upsertMessage(msg.role, msg.text, msg.final);
          } else if (msg.type === "tool_call") {
            setStatusMessage(`Processing...`);
          } else if (msg.type === "booking_success") {
            setStatusMessage("✅ Booking Confirmed");
            upsertMessage("system", "Appointment successfully saved to database.", true);
            onBookingSuccess?.();
          } else if (msg.type === "interrupt_tts") {
            if (currentPlayback.current) {
              currentPlayback.current.pause();
              currentPlayback.current = null;
            }
          }
          return;
        }

        const audioBuffer = event.data instanceof Blob ? await event.data.arrayBuffer() : event.data;
        const blob = new Blob([audioBuffer], { type: "audio/mpeg" });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        
        // Stop any currently playing audio to prevent overlap
        if (currentPlayback.current) {
          currentPlayback.current.pause();
          currentPlayback.current = null;
        }

        // Assistant Volume Analysis
        const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();

        const source = audioCtx.createMediaElementSource(audio);
        const analyzerNode = audioCtx.createAnalyser();
        analyzerNode.fftSize = 256;
        source.connect(analyzerNode);
        analyzerNode.connect(audioCtx.destination);
        updateVolume(analyzerNode);

        currentPlayback.current = audio;
        setIsSpeaking(true);
        audio.onended = () => {
          setIsSpeaking(false);
          if (animationFrame.current) cancelAnimationFrame(animationFrame.current);
          setVolume(0);
          audioCtx.close();
        };
        audio.play();
      };

      ws.current.onerror = () => {
        setErrorMessage("Connection Error. Is the backend running?");
        setConnectionState("error");
      };

      ws.current.onclose = () => stopRecording();

    } catch (err) {
      console.error(err);
      setErrorMessage("Microphone access denied.");
      setConnectionState("error");
    }
  };

  const stopRecording = () => {
    cleanupResources();
    setIsRecording(false);
    setIsSpeaking(false);
    setVolume(0);
    setConnectionState("standby");
    setStatusMessage("Session ended");
  };

  return (
    <div className="flex flex-col h-full max-h-full bg-[#0c0e14] rounded-3xl overflow-hidden border border-white/5 shadow-2xl relative">
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-8 py-8 space-y-6 scrollbar-hide bg-gradient-to-b from-transparent to-indigo-500/[0.02]"
      >
        {messages.filter(m => m.role !== 'system').map((msg, i) => (
          <div 
            key={i} 
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out`}
          >
            <div className={`px-5 py-3.5 rounded-3xl text-sm font-semibold tracking-tight shadow-sm transition-all hover:scale-[1.02] ${
              msg.role === 'user' 
                ? 'bg-indigo-600 text-white rounded-tr-none shadow-indigo-500/10' 
                : 'bg-slate-800/40 text-slate-100 rounded-tl-none backdrop-blur-md border border-white/5'
            }`}>
              {msg.text}
            </div>
            <span className="text-[8px] font-black text-slate-600 uppercase tracking-widest mt-2 px-1">
              {msg.role === 'user' ? 'Transmission' : 'Core Response'}
            </span>
          </div>
        ))}
      </div>

      <div className="shrink-0 flex flex-col items-center justify-center p-6 space-y-4 border-t border-white/5 bg-[#0c0e14]/90 backdrop-blur-xl relative">
        <div className="absolute -top-6 left-0 right-0 flex justify-center pointer-events-none">
          {(isRecording || isSpeaking) && (
            <div className="flex items-center justify-center gap-1.5 h-12 px-12 bg-gradient-to-t from-[#0c0e14] to-transparent w-full">
              {[...Array(30)].map((_, i) => (
                <div 
                  key={i}
                  className="w-1 bg-gradient-to-t from-indigo-500 via-blue-400 to-indigo-500 rounded-full animate-pulse transition-all duration-300"
                  style={{ 
                    height: `${20 + Math.random() * 80}%`,
                    animationDelay: `${i * 0.05}s`,
                    opacity: 0.4 + Math.random() * 0.6
                  }}
                />
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-6">
          <div className="relative group cursor-pointer transition-all duration-500 hover:scale-105" onClick={isRecording ? stopRecording : startRecording}>
            <AICore isActive={isRecording || isSpeaking} size={100} volume={volume} />
            
            <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 px-3 py-1 bg-cyan-600 rounded-full text-[8px] font-black text-white uppercase tracking-[0.2em] shadow-lg shadow-cyan-500/20 opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-y-1 group-hover:translate-y-0">
              {isRecording ? "Stop" : "Talk"}
            </div>
          </div>

          <div className="text-left space-y-1">
            <h2 className="text-lg font-black bg-gradient-to-b from-white via-white to-slate-500 bg-clip-text text-transparent tracking-tighter">
              {isRecording ? "Neural Link Active" : isSpeaking ? "Synthesizing" : "HealthSync Core"}
            </h2>
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full ${isRecording ? 'bg-indigo-500 animate-pulse' : 'bg-slate-700'}`} />
              <p className="text-[9px] text-slate-500 font-black uppercase tracking-[0.3em]">{statusMessage}</p>
            </div>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="px-6 py-4 bg-red-500/10 text-red-400 text-[10px] font-black text-center uppercase tracking-[0.2em] border-t border-red-500/20 backdrop-blur-md">
          Offline: {errorMessage}
        </div>
      )}
    </div>
  );
}

function downsampleBuffer(buffer: Float32Array, inputSampleRate: number, outputSampleRate: number) {
  if (inputSampleRate === outputSampleRate) return buffer;
  const ratio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    result[i] = buffer[Math.round(i * ratio)];
  }
  return result;
}

function float32ToInt16Buffer(buffer: Float32Array) {
  const l = buffer.length;
  const buf = new Int16Array(l);
  for (let i = 0; i < l; i++) {
    const s = Math.max(-1, Math.min(1, buffer[i]));
    buf[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return buf.buffer;
}
