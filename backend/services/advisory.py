def farmer_recommendations(temp: float, hum: float, wind: float, precip: float,
                           irr_mm: float, etc: float, et0: float):
    recs = {}

    # Irrigation
    if precip > 5:
        recs["irrigation"] = f"💧 Skip irrigation — rainfall expected ({precip:.1f} mm)."
    elif irr_mm > 5:
        recs["irrigation"] = f"🚜 Irrigate: {irr_mm:.1f} mm to meet crop needs (ETc={etc:.2f})."
    else:
        recs["irrigation"] = "✅ No irrigation needed — soil moisture adequate."

    # Pest
    if hum > 85 and 18 < temp < 28:
        recs["pest"] = "🐛 High fungal disease risk (blight/mildew). Consider protectant."
    elif hum < 40:
        recs["pest"] = "🪳 Low pest pressure — dry conditions."
    else:
        recs["pest"] = "⚠️ Moderate pest risk — scout regularly."

    # Field work
    if precip > 3 or hum > 90:
        recs["field"] = "❌ Too wet for tractor operations."
    elif wind > 7:
        recs["field"] = "🌬️ Windy — avoid spraying."
    else:
        recs["field"] = "✅ Good window for field work."

    # Frost
    if temp < 2:
        recs["frost"] = "❄️ Frost risk — protect seedlings."
    elif temp < 6:
        recs["frost"] = "⚠️ Mild cold risk — avoid night spraying."
    else:
        recs["frost"] = "🌡️ No frost risk."

    # Spray window
    if 50 < hum < 70 and wind < 5 and precip < 0.5:
        recs["spray"] = "💉 Excellent conditions for spraying (low wind, dry, moderate RH)."
    else:
        recs["spray"] = "🚫 Suboptimal spraying conditions."

    return recs
