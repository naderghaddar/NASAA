"use client"
import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { API, postJSON } from "./api"

type Resp = {
  target: string
  prediction: { Temp: number; Humidity: number; Wind: number; Precip: number }
  irrigation_mm: number
  et0: number
  etc: number
  peff: number
  recommendations: Record<string,string>
}

export default function Page() {
  const [form, setForm] = useState({
    lat: 45.65, lon: -73.38,
    target_date: new Date(Date.now()+3*864e5).toISOString().slice(0,10),
    kc: 1.15, soil_buffer_mm: 2, eff_rain_factor: 0.8
  })
  const [data, setData] = useState<Resp|null>(null)

  const run = useMutation({
    mutationFn: () => postJSON<Resp>(API("/api/forecast-advice"), {
      ...form, start:"20000709", end:"20250831"
    }),
    onSuccess: setData
  })

  return (
    <main className="p-6 max-w-5xl mx-auto">
      <h1 className="text-3xl font-semibold mb-4">🌾 Smart Irrigation & Advisory</h1>

      <div className="grid md:grid-cols-6 gap-3">
        <input className="input" value={form.lat} onChange={e=>setForm(f=>({...f, lat:+e.target.value}))} placeholder="Latitude"/>
        <input className="input" value={form.lon} onChange={e=>setForm(f=>({...f, lon:+e.target.value}))} placeholder="Longitude"/>
        <input className="input" type="date" value={form.target_date} onChange={e=>setForm(f=>({...f, target_date:e.target.value}))}/>
        <input className="input" type="number" step="0.05" value={form.kc} onChange={e=>setForm(f=>({...f, kc:+e.target.value}))} placeholder="Kc"/>
        <input className="input" type="number" value={form.soil_buffer_mm} onChange={e=>setForm(f=>({...f, soil_buffer_mm:+e.target.value}))} placeholder="Soil buffer (mm)"/>
        <input className="input" type="number" step="0.05" value={form.eff_rain_factor} onChange={e=>setForm(f=>({...f, eff_rain_factor:+e.target.value}))} placeholder="Eff rain"/>
      </div>
      <button onClick={()=>run.mutate()} className="mt-3 bg-black text-white rounded-lg px-4 py-2">Generate</button>
      <style jsx>{`.input { @apply rounded-lg border p-2 bg-white; }`}</style>

      {run.isPending && <p className="mt-6">Running…</p>}
      {data && (
        <div className="mt-6 space-y-3">
          <div className="rounded-xl border p-4 bg-white">
            <div className="font-medium">Forecast for {data.target}</div>
            <div className="grid md:grid-cols-5 gap-3 mt-2">
              <div>🌡 Temp: <b>{data.prediction.Temp.toFixed(1)} °C</b></div>
              <div>💧 Humidity: <b>{data.prediction.Humidity.toFixed(0)} %</b></div>
              <div>🌬 Wind: <b>{data.prediction.Wind.toFixed(2)} m/s</b></div>
              <div>🌦 Precip: <b>{data.prediction.Precip.toFixed(2)} mm</b></div>
              <div>💦 Irrigation: <b>{data.irrigation_mm.toFixed(2)} mm</b> <span className="text-xs text-gray-500">(ET0 {data.et0.toFixed(2)} | ETc {data.etc.toFixed(2)} | EffRain {data.peff.toFixed(2)})</span></div>
            </div>
          </div>
          <div className="rounded-xl border p-4 bg-white">
            <div className="font-medium">Farm Advisory</div>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>{data.recommendations.irrigation}</li>
              <li>{data.recommendations.pest}</li>
              <li>{data.recommendations.field}</li>
              <li>{data.recommendations.spray}</li>
              <li>{data.recommendations.frost}</li>
            </ul>
          </div>
        </div>
      )}
    </main>
  )
}
