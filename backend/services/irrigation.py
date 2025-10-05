import math
from datetime import date as _date

def extraterrestrial_radiation(latitude: float, doy: int) -> float:
    phi = math.radians(latitude)
    dr = 1 + 0.033 * math.cos(2*math.pi*doy/365)
    delta = 0.409 * math.sin(2*math.pi*doy/365 - 1.39)
    omega_s = math.acos(-math.tan(phi)*math.tan(delta))
    Gsc = 0.0820  # MJ m^-2 min^-1
    return (24*60/math.pi)*Gsc*dr*(omega_s*math.sin(phi)*math.sin(delta) +
                                   math.cos(phi)*math.cos(delta)*math.sin(omega_s))

def estimate_trange(temp: float, humidity: float, wind: float) -> float:
    tr = 12 + (50 - humidity)*0.03 + wind*0.6
    return max(6.0, min(tr, 16.0))

def et0_hargreaves(temp: float, humidity: float, wind: float, lat: float, date: _date) -> float:
    doy = date.timetuple().tm_yday
    tr = estimate_trange(temp, humidity, wind)
    Ra = extraterrestrial_radiation(lat, doy)
    return max(0.0, 0.0023 * (temp + 17.8) * math.sqrt(tr) * Ra)

def irrigation_need(temp: float, humidity: float, wind: float, precip: float,
                    lat: float, date: _date, kc: float,
                    eff_rain_factor: float = 0.8, soil_buffer_mm: float = 2.0):
    et0 = et0_hargreaves(temp, humidity, wind, lat, date)
    etc = kc * et0
    peff = eff_rain_factor * max(0.0, precip)
    net = max(0.0, etc - peff - soil_buffer_mm)
    return net, et0, etc, peff
