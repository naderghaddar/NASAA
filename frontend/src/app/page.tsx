"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { API, postJSON } from "./api";

type Resp = {
  target: string;
  prediction: { Temp: number; Humidity: number; Wind: number; Precip: number };
  irrigation_mm: number;
  et0: number;
  etc: number;
  peff: number;
  recommendations: Record<string, string>;
};

export default function Landing() {
  const [form, setForm] = useState({
    lat: 45.65,
    lon: -73.38,
    target_date: new Date(Date.now() + 3 * 864e5).toISOString().slice(0, 10),
    kc: 1.15,
    soil_buffer_mm: 2,
    eff_rain_factor: 0.8,
  });
  const [data, setData] = useState<Resp | null>(null);

  const run = useMutation({
    mutationFn: () => {
      // Build YYYYMMDD strings
      //const endStr = form.target_date.replaceAll("-", "");
      //const startYear = String(Number(form.target_date.slice(0,4)) - 25); // last 25y
      //const startStr = startYear + endStr.slice(4); // keep same MMDD

      return postJSON<Resp>(API("/api/forecast-advice"), {
        ...form,
        start: "20000709", //hardcoded data (last 25years)
        end: "20250831",
      });
    },
    onSuccess: setData,
  });

  console.log(run);


  const input =
    "w-full rounded-xl border border-white/20 bg-white/5 text-white placeholder-white/60 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-white/40";
  const label = "text-xs uppercase tracking-wide text-white/70";

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Blue info strip (like NASA banner) */}
      <div className="w-full bg-[#0B5FFF] text-[10px] text-white/95 text-center py-2">
        <p>2025 NASA Space Apps Challenge : Will It Rain On My Parade?</p>
      </div>

      {/* Slim header / nav */}
      <header className="flex items-center justify-between px-6 lg:px-12 py-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-white/10 grid place-items-center font-bold">
            🌙
          </div>
          <span className="text-sm text-white/70">Explore</span>
        </div>
        <div><img width="80" height="48" src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/NASA-Logo.svg/2516px-NASA-Logo.svg.png" alt="Nasa" /></div>
        <nav className="hidden md:flex items-center gap-6 text-sm text-white/70">
          <span>News & Events</span>
        </nav>
      </header>

      

      {/* HERO */}
      <section className="relative overflow-hidden isolate">
        {/* Background image (moon/space). Put your file at /public/hero-moon.jpg */}
        <div
          className="absolute inset-0 -z-10 bg-center bg-no-repeat bg-cover opacity-80"
          style={{ backgroundImage: "url('https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=1950&q=80')" }}
          aria-hidden= "true"
        />
        {/* Subtle black gradient for contrast */}
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-black via-black/60 to-black/30" />

        <div className="mx-auto max-w-7xl px-6 lg:px-12 py-14 lg:py-24 min-h-[70vh] grid content-center">
          {/* Big NASA-style headline */}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-[1.05] max-w-3xl">
            Return to the <span className="text-white/70">Field</span>
          </h1>
          <p className="mt-5 text-lg text-white/80 max-w-2xl">
            Smart Irrigation & Advisory—driven by NASA POWER climatology and a
            transparent Random Forest model. Plan irrigation, avoid risky
            windows, and get clear actions.
          </p>

          {/* GLASS FORM CARD */}
          <div className="mt-10 max-w-4xl">
            <div className="rounded-2xl border border-white/15 bg-white/5 backdrop-blur-xl shadow-2xl p-5 sm:p-6 lg:p-8">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  run.mutate();
                }}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
              >
                <div>
                  <div className={label}>Latitude</div>
                  <input
                    className={input}
                    type="number"
                    step="0.0001"
                    value={form.lat}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, lat: +e.target.value }))
                    }
                  />
                </div>
                <div>
                  <div className={label}>Longitude</div>
                  <input
                    className={input}
                    type="number"
                    step="0.0001"
                    value={form.lon}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, lon: +e.target.value }))
                    }
                  />
                </div>
                <div>
                  <div className={label}>Target Date</div>
                  <input
                    className={input}
                    type="date"
                    value={form.target_date}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, target_date: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <div className={label}>Kc (crop coefficient)</div>
                  <input
                    className={input}
                    type="number"
                    step="0.05"
                    value={form.kc}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, kc: +e.target.value }))
                    }
                  />
                </div>
                <div>
                  <div className={label}>Soil buffer (mm)</div>
                  <input
                    className={input}
                    type="number"
                    value={form.soil_buffer_mm}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        soil_buffer_mm: +e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <div className={label}>Effective rain factor</div>
                  <input
                    className={input}
                    type="number"
                    step="0.05"
                    value={form.eff_rain_factor}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        eff_rain_factor: +e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="sm:col-span-2 lg:col-span-3 flex items-center gap-4">
                  <button
                    type="submit"
                    disabled={run.isPending}
                    className="inline-flex items-center justify-center rounded-xl bg-white text-black font-semibold px-5 py-2.5 hover:bg-white/90 transition disabled:opacity-60"
                  >
                    {run.isPending ? "Generating…" : "Generate Advisory"}
                  </button>
                  <span className="text-sm text-white/60">
                    Uses recent climatology for speed; first run can take a bit.
                  </span>
                </div>
              </form>
            </div>
          </div>

          {/* Small status line */}
          {run.isError && (
            <p className="mt-4 text-red-300">
              Error: {(run.error as Error)?.message}
            </p>
          )}
        </div>
      </section>

      {/* RESULTS SECTION (below the fold, light card on dark bg) */}
      {run.isSuccess && data &&  (
        <section id="results" className="px-6 lg:px-12 py-12 bg-gradient-to-b from-black to-[#0b0b0b]">
          <div className="mx-auto max-w-6xl">
            <h2 className="text-2xl font-semibold mb-4">
              📊 Results for {data.target}
            </h2>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <Card label="🌡 Temp" value={`${data.prediction.Temp.toFixed(1)} °C`} />
              <Card label="💧 Humidity" value={`${data.prediction.Humidity.toFixed(0)} %`} />
              <Card label="🌬 Wind" value={`${data.prediction.Wind.toFixed(2)} m/s`} />
              <Card label="🌦 Precip" value={`${data.prediction.Precip.toFixed(2)} mm`} />
              <Card
                label="💦 Irrigation"
                value={`${data.irrigation_mm.toFixed(2)} mm`}
                tip={`ET₀ ${data.et0.toFixed(2)} | ETc ${data.etc.toFixed(2)} | EffRain ${data.peff.toFixed(2)}`}
              />
            </div>

            <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-6">
              <h3 className="font-medium mb-2">Farm Advisory</h3>
              <ul className="space-y-2 text-[15px] leading-6 text-white/90">
                <li>• {data.recommendations.irrigation}</li>
                <li>• {data.recommendations.pest}</li>
                <li>• {data.recommendations.field}</li>
                <li>• {data.recommendations.spray}</li>
                <li>• {data.recommendations.frost}</li>
              </ul>
            </div>
          </div>
        </section>
      )}

      <footer className="px-6 lg:px-12 py-10 text-xs text-white/50">
        NASA POWER data • Built for demo purposes
      </footer>
    </main>
  );
}

function Card({ label, value, tip }: { label: string; value: string; tip?: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="text-xs uppercase tracking-wide text-white/60">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {tip && <div className="text-xs text-white/50 mt-1">{tip}</div>}
    </div>
  );
}
