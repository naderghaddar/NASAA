import { useState } from "react";
import "./index.css";
import { predict } from "./api";

export default function App() {
  const [form, setForm] = useState({
    lat: -14.65, //Brasil coordinates
    lon: -51.38, //brasil coordinates
    target_date: "2026-06-01",
    kc: 1.1,
    soil_buffer: 2
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setData(null);
    try {
      const result = await predict(form);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>🌾 Smart Irrigation Dashboard</h1>
        <p className="subtitle">
          Plan your farm irrigation!
        </p>
      </header>

      <form onSubmit={handleSubmit} className="form">
        <div className="form-row">
          <label>Latitude</label>
          <input name="lat" type="number" step="0.01" value={form.lat} onChange={handleChange} />
        </div>
        <div className="form-row">
          <label>Longitude</label>
          <input name="lon" type="number" step="0.01" value={form.lon} onChange={handleChange} />
        </div>
        <div className="form-row">
          <label>Target date</label>
          <input name="target_date" type="date" value={form.target_date} onChange={handleChange} />
        </div>
        <div className="form-row">
          <label>Crop coefficient (Kc)</label>
          <input name="kc" type="number" step="0.05" value={form.kc} onChange={handleChange} />
        </div>
        <div className="form-row">
          <label>Soil buffer (mm)</label>
          <input name="soil_buffer" type="number" step="1" value={form.soil_buffer} onChange={handleChange} />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? "Predicting..." : "🌤️ Predict"}
        </button>
      </form>

      {error && <p className="error">❌ {error}</p>}

      {data && (
        <div className="results">
          <h2>🌦️ Forecast for {form.target_date}</h2>
          <div className="cards">
            <div className="card weather">
              <h3>Weather Conditions</h3>
              <p>🌡️ <strong>{data.prediction.temp}</strong> °C</p>
              <p>💧 <strong>{data.prediction.humidity}</strong> % Humidity</p>
              <p>🌬️ <strong>{data.prediction.wind}</strong> m/s Wind</p>
              <p>🌦️ <strong>{data.prediction.precip}</strong> mm Rain</p>
            </div>

            <div className="card irrigation">
              <h3>Irrigation Summary</h3>
              <p>💦 <strong>{data.irrigation.irr_mm}</strong> mm Water Needed</p>
              <p>📈 ET₀: {data.irrigation.et0}</p>
              <p>🌿 ETc: {data.irrigation.etc}</p>
              <p>🌧️ EffRain: {data.irrigation.peff}</p>
            </div>
          </div>

          <div className="advisory">
            <h3>🌾 Farm Advisory</h3>
            <div className="advice-grid">
              <div className="advice irrigation">{data.advisory.irrigation}</div>
              <div className="advice pest">{data.advisory.pest}</div>
              <div className="advice field">{data.advisory.field}</div>
              <div className="advice frost">{data.advisory.frost}</div>
              <div className="advice spray">{data.advisory.spray}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
