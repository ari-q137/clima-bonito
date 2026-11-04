from datetime import datetime, timedelta
import math
import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components
from zoneinfo import ZoneInfo




# Configuración inicial de la página
st.set_page_config(
    page_title="Clima Bonito • App del Clima", 
    page_icon="🌸", 
    layout="wide",
    initial_sidebar_state="expanded"
)



# --- CONSULTA A APIS CON PROTECCIÓN TOTAL CONTRA BLOQUEOS ---
@st.cache_data(ttl=3600, show_spinner=False)
def obtener_clima_api(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,relative_humidity_2m_mean,weathercode,uv_index_max&hourly=temperature_2m,precipitation_probability,relative_humidity_2m,weathercode&timezone=auto"
        response = requests.get(url, timeout=1.5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=86400, show_spinner=False)
def obtener_sugerencias_ubicacion(query):
    if not query or len(query.strip()) < 2:
        return []
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=5&language=es&format=json"
        response = requests.get(url, timeout=1.0)
        if response.status_code == 200:
            data = response.json()
            if "results" in data:
                sugerencias = []
                for res in data["results"]:
                    nombre = res.get("name", "")
                    admin = res.get("admin1", "")
                    pais = res.get("country", "")
                    sugerencias.append({
                        "etiqueta": f"{nombre}, {admin}, {pais}" if admin else f"{nombre}, {pais}",
                        "lat": res.get("latitude"),
                        "lon": res.get("longitude"),
                        "nombre_corto": nombre,
                        "estado": admin,
                    })
                return sugerencias
    except Exception:
        pass
    return []

def interpretar_weathercode(code, hora=12, minuto=0):
    minutos_totales = hora * 60 + minuto
    es_noche = minutos_totales < 360 or minutos_totales >= 1110
    if code is None or code == 0:
        return ("Noche despejada", "🌙") if es_noche else ("Soleado", "☀️")
    elif code in [1, 2]:
        return ("Noche parcialmente nublada", "☁️🌙") if es_noche else ("Parcialmente nublado", "⛅")
    elif code in [3, 45, 48]:
        return ("Noche nublada", "☁️🌙") if es_noche else ("Nublado", "☁️")
    elif code in [95, 96, 99]:
        return ("Tormenta eléctrica nocturna", "⚡🌙") if es_noche else ("Tormenta eléctrica", "⚡")
    elif code in [71, 73, 75, 77, 85, 86]:
        return ("Noche nevada", "❄️🌙") if es_noche else ("Nevado", "❄️")
    elif code >= 50 and code < 90:
        return ("Noche lluviosa", "🌧️🌙") if es_noche else ("Lluvioso", "🌧️")
    else:
        return ("Noche despejada", "🌙") if es_noche else ("Soleado", "☀️")

# --- ESTADOS DE LA SESIÓN ---
if "vista_detalle" not in st.session_state:
    st.session_state.vista_detalle = False
if "vista_museo" not in st.session_state:
    st.session_state.vista_museo = False
if "dia_seleccionado" not in st.session_state:
    st.session_state.dia_seleccionado = 0
if "unidades_temp" not in st.session_state:
    st.session_state.unidades_temp = "°C"
if "easter_egg_activo" not in st.session_state:
    st.session_state.easter_egg_activo = False

TEMAS_CLIMA_OSCURO = {
    "Soleado": {"bg": "#241B17", "card": "#362721", "accent": "#FFB703", "text": "#FFE6D5", "subtext": "#FFD1A3", "badge": "#FFB70333", "sidebar": "#2C201B", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Parcialmente nublado": {"bg": "#1C1D24", "card": "#282936", "accent": "#FFD166", "text": "#F4F5F6", "subtext": "#A0AAB2", "badge": "#FFD16633", "sidebar": "#22232D", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Nublado": {"bg": "#1A1726", "card": "#262138", "accent": "#FF80BF", "text": "#E8D7F1", "subtext": "#B5A1E8", "badge": "#FF80BF33", "sidebar": "#211C30", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Lluvioso": {"bg": "#131C26", "card": "#1E2B3B", "accent": "#38B6FF", "text": "#D6EEFF", "subtext": "#80CAFF", "badge": "#38B6FF33", "sidebar": "#182330", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Tormenta eléctrica": {"bg": "#0D1117", "card": "#161B22", "accent": "#F72585", "text": "#F8D7DA", "subtext": "#F28482", "badge": "#F7258533", "sidebar": "#090D12", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Nevado": {"bg": "#162026", "card": "#202E38", "accent": "#90E0EF", "text": "#E0FBFC", "subtext": "#A5F0FC", "badge": "#90E0EF33", "sidebar": "#1B2730", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Noche despejada": {"bg": "#0B0E14", "card": "#151B26", "accent": "#A0C4FF", "text": "#E2E8F0", "subtext": "#8D99AE", "badge": "#A0C4FF33", "sidebar": "#0F141E", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Noche parcialmente nublada": {"bg": "#0E1320", "card": "#1A2130", "accent": "#B9FBC0", "text": "#E2E8F0", "subtext": "#94A3B8", "badge": "#B9FBC033", "sidebar": "#131926", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Noche nublada": {"bg": "#121622", "card": "#1E2436", "accent": "#BDB2FF", "text": "#ECE7FE", "subtext": "#9D8EC7", "badge": "#BDB2FF33", "sidebar": "#161B29", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Noche lluviosa": {"bg": "#0F172A", "card": "#1E293B", "accent": "#38BDF8", "text": "#E0F2FE", "subtext": "#7DD3FC", "badge": "#38BDF833", "sidebar": "#131F33", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Tormenta eléctrica nocturna": {"bg": "#0B0F19", "card": "#171E31", "accent": "#E879F9", "text": "#FAE8FF", "subtext": "#D946EF", "badge": "#E879F933", "sidebar": "#0D1322", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
    "Noche nevada": {"bg": "#111C24", "card": "#1C2D37", "accent": "#CAF0F8", "text": "#EDF6F9", "subtext": "#90E0EF", "badge": "#CAF0F833", "sidebar": "#14222B", "val_color": "#FFFFFF", "input_text": "#FFFFFF"},
}

with st.sidebar:
    st.markdown("<h3 style='text-align: center; margin-bottom: 0px;'>🐾 Configuración</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 0.8rem; opacity: 0.7; margin-top: 0px;'>Personaliza tu aplicación</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)

    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; margin-bottom: 4px;'>📍 Buscar Ubicación:</p>", unsafe_allow_html=True)
    busqueda_texto = st.text_input("Ubicación:", "Saltillo", label_visibility="collapsed")
    
    lista_sugerencias = obtener_sugerencias_ubicacion(busqueda_texto)
    
    if lista_sugerencias:
        opciones_map = {s["etiqueta"]: s for s in lista_sugerencias}
        seleccion_usuario = st.selectbox("Sugerencias", list(opciones_map.keys()), label_visibility="collapsed")
        ubicacion_elegida = opciones_map[seleccion_usuario]
        municipio_limpio = ubicacion_elegida["nombre_corto"]
        estado_limpio = ubicacion_elegida["estado"]
        lat_actual = ubicacion_elegida["lat"]
        lon_actual = ubicacion_elegida["lon"]
    else:
        municipio_limpio = "Saltillo"
        estado_limpio = "Coahuila"
        lat_actual = 25.4232
        lon_actual = -101.0053

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🐱 Museo de Gatitos", use_container_width=True):
        st.session_state.vista_museo = True
        st.session_state.vista_detalle = False
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    datos_api_temporal = obtener_clima_api(lat_actual, lon_actual)

    def obtener_condicion_por_hora_actual(datos_api):
        try:
            zona_mx = ZoneInfo("America/Monterrey")
            ahora_mx = datetime.now(zona_mx)
        except Exception:
            ahora_mx = datetime.now()
        hora_actual = ahora_mx.hour
        minuto_actual = ahora_mx.minute
        if datos_api and "hourly" in datos_api:
            try:
                idx_hora = hora_actual
                temp_h = datos_api["hourly"]["temperature_2m"][idx_hora]
                lluvia_h = datos_api["hourly"].get("precipitation_probability", [10]*24)[idx_hora] or 10
                if "weathercode" in datos_api["hourly"]:
                    code = datos_api["hourly"]["weathercode"][idx_hora]
                    cond, icono = interpretar_weathercode(code, hora=hora_actual, minuto=minuto_actual)
                    return cond, icono, temp_h, lluvia_h
            except Exception:
                pass
        minutos_totales = hora_actual * 60 + minuto_actual
        es_noche = minutos_totales < 360 or minutos_totales >= 1110
        return ("Noche despejada" if es_noche else "Soleado"), ("🌙" if es_noche else "☀️"), 22.0, 15

    clima_hoy, _, _, _ = obtener_condicion_por_hora_actual(datos_api_temporal)
    cfg = TEMAS_CLIMA_OSCURO.get(clima_hoy, TEMAS_CLIMA_OSCURO["Nublado"])

    html_reloj_cute = f"""
    <div style="background: {cfg['card']}; border: 2.5px dashed {cfg['accent']}; border-radius: 20px; padding: 12px; text-align: center; font-family: 'Quicksand', sans-serif; box-shadow: 0 4px 12px {cfg['accent']}33;">
        <div id="relojContainer" style="font-size: 1.5rem; font-weight: 700; color: {cfg['val_color']}; display: flex; align-items: center; justify-content: center; gap: 6px;">
            <span id="relojHora">00:00:00</span>
            <span id="relojAmpm" style="font-size: 0.85rem; color: {cfg['accent']};">AM</span>
        </div>
        <div id="relojFecha" style="font-size: 0.75rem; color: {cfg['subtext']}; font-weight: 600; margin-top: 4px;"></div>
    </div>
    <script>
        function actualizarReloj() {{
            const ahora = new Date();
            const opcionesFecha = {{ timeZone: 'America/Monterrey', weekday: 'short', day: 'numeric', month: 'short' }};
            const opcionesHora = {{ timeZone: 'America/Monterrey', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }};
            const formatterHora = new Intl.DateTimeFormat('en-US', opcionesHora);
            const partesHora = formatterHora.formatToParts(ahora);
            let h = '00', m = '00', s = '00';
            partesHora.forEach(p => {{
                if (p.type === 'hour') h = p.value;
                if (p.type === 'minute') m = p.value;
                if (p.type === 'second') s = p.value;
            }});
            let horaInt = parseInt(h, 10);
            const ampm = horaInt >= 12 ? 'PM' : 'AM';
            horaInt = horaInt % 12;
            horaInt = horaInt ? horaInt : 12;
            const horaStr = String(horaInt).padStart(2, '0') + ':' + m + ':' + s;
            document.getElementById('relojHora').innerText = horaStr;
            document.getElementById('relojAmpm').innerText = ampm;
            const formatterFecha = new Intl.DateTimeFormat('es-ES', opcionesFecha);
            document.getElementById('relojFecha').innerText = formatterFecha.format(ahora);
        }}
        setInterval(actualizarReloj, 1000);
        actualizarReloj();
    </script>
    """
    components.html(html_reloj_cute, height=95)

    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; margin-bottom: 2px;'>🌡️ Unidades de Temperatura:</p>", unsafe_allow_html=True)
    unidades_sel = st.selectbox("Unidades", ("°C", "°F"), label_visibility="collapsed")
    if unidades_sel != st.session_state.unidades_temp:
        st.session_state.unidades_temp = unidades_sel
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; margin-bottom: 2px;'>🎶 Radio Lo-Fi:</p>", unsafe_allow_html=True)
    
    html_lofi = f"""
    <div style="background: {cfg['card']}; border: 1.5px solid {cfg['accent']}66; border-radius: 16px; padding: 12px; font-family: 'Quicksand', sans-serif; color: {cfg['text']}; box-shadow: 0 4px 12px {cfg['accent']}22;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 0.8rem; font-weight: 700; color: {cfg['accent']};">🎧 Chill Beats 24/7</span>
            <span style="font-size: 0.7rem; opacity: 0.7;">En vivo</span>
        </div>
        <audio id="audioLofi" preload="none" loop>
            <source src="https://stream.zeno.fm/f3wvbbqmdg8uv" type="audio/mp4">
        </audio>
        <button onclick="togglePlay()" id="btnPlay" style="background: {cfg['accent']}; color: #222; border: none; border-radius: 10px; padding: 7px; font-weight: bold; cursor: pointer; font-size: 0.8rem; width: 100%; transition: 0.2s;">▶️ Reproducir</button>
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 8px;">
            <span style="font-size: 0.7rem;">🔈</span>
            <input type="range" id="volSlider" min="0" max="1" step="0.01" value="0.05" oninput="setVol(this.value)" style="width: 100%; accent-color: {cfg['accent']}; cursor: pointer;">
            <span style="font-size: 0.7rem;">🔊</span>
        </div>
    </div>
    <script>
        const audio = document.getElementById('audioLofi');
        audio.volume = 0.05;
        function togglePlay() {{
            const btn = document.getElementById('btnPlay');
            if (audio.paused) {{
                audio.play().then(() => {{
                    btn.innerHTML = "⏸️ Pausa";
                }}).catch(() => {{}});
            }} else {{
                audio.pause();
                btn.innerHTML = "▶️ Reproducir";
            }}
        }}
        function setVol(val) {{ audio.volume = val; }}
    </script>
    """
    components.html(html_lofi, height=130)
    
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
        <div style="background: {cfg['card']}; border: 1.5px dashed {cfg['accent']}88; border-radius: 12px; padding: 8px 10px; text-align: center; margin-bottom: 8px;">
            <span style="font-size: 0.75rem; color: {cfg['subtext']}; font-weight: 600; line-height: 1.2; display: block;">
                💖 Pica con mucho amor el botón <b style="color: {cfg['accent']};">"Ekuipo"</b> para desbloquear una pequeña sorpresa mágica ✨🐾
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Usamos una clave única y manejamos el estado sin forzar un st.rerun inmediato peligroso
if st.button("✨ Ekuipo", use_container_width=True, key="btn_ekuipo_magico"):
        st.session_state.easter_egg_activo = not st.session_state.easter_egg_activo

if st.session_state.get("easter_egg_activo", False):
        st.balloons()
        st.success("Ekuipo conformado por Ari y Angela 🐾✨")

def convertir_temp(celsius):
    if st.session_state.unidades_temp == "°F":
        return round((celsius * 9/5) + 32, 1)
    return round(celsius, 1)

def obtener_gatito_segun_clima(t_c, uv_val=5.0):
    if t_c in ["Soleado"]:
        consejo = "¡Solcito hermoso! Usa tus lentes de sol 🕶️✨" if uv_val < 8 else f"¡Sol muy fuerte! (UV {uv_val}) 🧴✨"
        ojos_html = '<div class="lentes-css-ojos"><div class="cristal izq"></div><div class="puente"></div><div class="cristal der"></div></div>'
        accesorio_html = '<div class="icono-clima-flotante">☀️</div>'
    elif "Parcialmente nublado" in t_c:
        consejo = "Ratos de sol y nubes ~ ⛅"
        ojos_html = '<div class="ojitos"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">⛅</div>'
    elif "Noche parcialmente nublada" in t_c:
        consejo = "Noche fresca con nubes pasajeras ☁️🌙"
        ojos_html = '<div class="ojitos-durmiendo"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">☁️</div>'
    elif "Noche despejada" in t_c:
        consejo = "¡Buenas noches! Estrellas brillando 🌙✨"
        ojos_html = '<div class="ojitos-durmiendo"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">🌙</div>'
    elif "Noche nublada" in t_c:
        consejo = "Noche nubladita y calmada ~ ☁️🌙"
        ojos_html = '<div class="ojitos-durmiendo"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">☁️</div>'
    elif "Noche lluviosa" in t_c:
        consejo = "Lluvia de medianoche 🌧️🌙"
        ojos_html = '<div class="ojitos-durmiendo"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">🌧️</div>'
    elif "Tormenta eléctrica nocturna" in t_c:
        consejo = "Rayos iluminando la noche ⚡🌙"
        ojos_html = '<div class="ojitos"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">⚡</div>'
    elif "Noche nevada" in t_c:
        consejo = "Silencio blanco y frío ❄️🌙"
        ojos_html = '<div class="ojitos-durmiendo"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">❄️</div>'
    elif t_c in ["Lluvioso"]:
        consejo = "Escucha las gotitas caer ☂️🌧️"
        ojos_html = '<div class="ojitos"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">☂️</div>'
    elif t_c in ["Tormenta eléctrica"]:
        consejo = "Truenos y rayos, un chocolatito caliente ⚡☕"
        ojos_html = '<div class="ojitos"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">⚡</div>'
    elif t_c == "Nublado":
        consejo = "Día nubladito y fresco ~ ☁️"
        ojos_html = '<div class="ojitos-durmiendo"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">☁️</div>'
    else:
        consejo = "Abrígate bien con tu bufanda 🧣❄️"
        ojos_html = '<div class="ojitos"><span></span><span></span></div>'
        accesorio_html = '<div class="icono-clima-flotante">🧣</div>'

    return f"""
        <div class="tarjeta-gatito-box">
            <div class="gato-avatar">
                <div class="oreja izq"></div>
                <div class="oreja der"></div>
                <div class="cara">
                    {ojos_html}
                    <div class="hocico">ω</div>
                </div>
                {accesorio_html}
            </div>
            <div class="burbuja-texto">
                <span class="frase-cat">{consejo}</span>
            </div>
        </div>
    """

def generar_pronostico_inteligente(lat, lon):
    datos_api = obtener_clima_api(lat, lon)
    try:
        zona_mx = ZoneInfo("America/Monterrey")
        hoy = datetime.now(zona_mx)
    except Exception:
        hoy = datetime.now()

    predicciones = []
    meses_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre",
        12: "Diciembre",
    }

    for i in range(4):
        d_obj = hoy + timedelta(days=i)
        fecha_str = f"{d_obj.day} de {meses_es[d_obj.month]}"
        etiqueta = f"Hoy • {fecha_str}" if i == 0 else (f"Mañana • {fecha_str}" if i == 1 else fecha_str)

        tmax, tmin, hum, lluvia, uv_val = 24.0, 12.0, 45, 10, 5.0
        t_c, icono = "Soleado", "☀️"

        if datos_api and "daily" in datos_api:
            try:
                tmax = datos_api["daily"]["temperature_2m_max"][i]
                tmin = datos_api["daily"]["temperature_2m_min"][i]
                lluvia = datos_api["daily"].get("precipitation_probability_max", [20]*4)[i] or 15
                hum = datos_api["daily"].get("relative_humidity_2m_mean", [50]*4)[i] or 50
                uv_val = datos_api["daily"].get("uv_index_max", [5.0]*4)[i] or 5.0
                if "weathercode" in datos_api["daily"]:
                    w_code = datos_api["daily"]["weathercode"][i]
                    t_c, icono = interpretar_weathercode(w_code, hora=12, minuto=0)
            except Exception:
                pass

        def obtener_condicion_por_hora_actual_local(datos_api_arg):
            try:
                zona_mx_l = ZoneInfo("America/Monterrey")
                ahora_mx_l = datetime.now(zona_mx_l)
            except Exception:
                ahora_mx_l = datetime.now()
            hora_actual_l = ahora_mx_l.hour
            minuto_actual_l = ahora_mx_l.minute
            if datos_api_arg and "hourly" in datos_api_arg:
                try:
                    idx_hora_l = hora_actual_l
                    temp_h_l = datos_api_arg["hourly"]["temperature_2m"][idx_hora_l]
                    lluvia_h_l = datos_api_arg["hourly"].get("precipitation_probability", [10]*24)[idx_hora_l] or 10
                    if "weathercode" in datos_api_arg["hourly"]:
                        code_l = datos_api_arg["hourly"]["weathercode"][idx_hora_l]
                        cond_l, icono_l = interpretar_weathercode(code_l, hora=hora_actual_l, minuto=minuto_actual_l)
                        return cond_l, icono_l, temp_h_l, lluvia_h_l
                except Exception:
                    pass
            minutos_totales_l = hora_actual_l * 60 + minuto_actual_l
            es_noche_l = minutos_totales_l < 360 or minutos_totales_l >= 1110
            return ("Noche despejada" if es_noche_l else "Soleado"), ("🌙" if es_noche_l else "☀️"), 22.0, 15

        if i == 0 and datos_api:
            cond_h, icono_h, _, lluvia_h = obtener_condicion_por_hora_actual_local(datos_api)
            t_c = cond_h
            icono = icono_h
            lluvia = lluvia_h

        gatito_html = obtener_gatito_segun_clima(t_c, uv_val)

        predicciones.append({
            "ID": i,
            "FechaTitulo": etiqueta,
            "TMAX": convertir_temp(tmax),
            "TMIN": convertir_temp(tmin),
            "Humedad": int(hum),
            "Lluvia": int(lluvia),
            "UV": round(uv_val, 1),
            "Tipo": t_c,
            "Icono": icono,
            "GatitoHtml": gatito_html,
        })
    return pd.DataFrame(predicciones), datos_api

df_p, datos_api_raw = generar_pronostico_inteligente(lat_actual, lon_actual)

cond_actual_real, icono_actual_real = "Soleado", "☀️"
if not df_p.empty:
    cond_actual_real = df_p.iloc[0]["Tipo"]
    icono_actual_real = df_p.iloc[0]["Icono"]

def generar_html_animacion_fondo(tipo_clima):
    tc = tipo_clima.lower()
    if "noche despejada" in tc or tc == "noche despejada":
        estrellas = "".join([f'<div class="estrella-noche" style="left: {(i*11)%95}%; top: {(i*13)%85}%; animation-delay: {(i*0.3)%2}s;">✨</div>' for i in range(22)])
        return f'<div class="clima-anim-box"><div class="cometa-veloz-bg"></div><div class="luna-noche">🌙</div>{estrellas}</div>'
    elif "noche parcialmente" in tc:
        nubes = "".join([f'<div class="nube-desplazandose" style="top: {(12 + i*25)}%; animation-duration: {14 + (i%3)*3}s; animation-delay: {i*2}s;">☁️</div>' for i in range(4)])
        return f'<div class="clima-anim-box"><div class="luna-noche" style="opacity: 0.8;">🌙</div>{nubes}</div>'
    elif "noche nublada" in tc:
        nubes_oscuras = "".join([f'<div class="nube-desplazandose-lenta" style="top: {(8 + i*18)}%; animation-duration: {10 + (i%4)*2.5}s; animation-delay: {i*1.2}s;">☁️</div>' for i in range(7)])
        return f'<div class="clima-anim-box"><div class="nebulosa-nocturna"></div>{nubes_oscuras}</div>'
    elif "noche lluviosa" in tc:
        gotas = "".join([f'<div class="gota-noche" style="left: {i*6}%; animation-delay: {(i*0.07)%1}s;"></div>' for i in range(18)])
        return f'<div class="clima-anim-box"><div class="luna-noche" style="opacity: 0.6;">🌙</div>{gotas}<div class="radar-nocturno"></div></div>'
    elif "tormenta eléctrica nocturna" in tc:
        gotas = "".join([f'<div class="gota-noche-intensa" style="left: {i*6}%; animation-delay: {(i*0.05)%1}s;"></div>' for i in range(20)])
        return f'<div class="clima-anim-box"><div class="flash-rayo-pantalla-noche"></div><div class="luna-noche" style="opacity: 0.4;">🌙</div>{gotas}</div>'
    elif "noche nevada" in tc:
        copos = "".join([f'<div class="copo-noche" style="left: {i*8}%; animation-delay: {(i*0.2)%2}s;">❄️</div>' for i in range(14)])
        return f'<div class="clima-anim-box"><div class="luna-noche">🌙</div><div class="aura-fria"></div>{copos}</div>'
    elif "soleado" in tc or tc == "soleado":
        particulas_sol = "".join([f'<div class="particula-destello-sol" style="left: {(i*19)%92}%; top: {(i*15)%78}%; animation-delay: {(i*0.4)%3}s;">✨</div>' for i in range(12)])
        return f'<div class="clima-anim-box"><div class="sol-dia-anim">☀️</div>{particulas_sol}</div>'
    elif "parcialmente nublado" in tc:
        nubes = "".join([f'<div class="nube-desplazandose" style="top: {(10 + i*28)}%; animation-duration: {12 + (i%3)*3}s; animation-delay: {i*1.8}s;">☁️</div>' for i in range(4)])
        return f'<div class="clima-anim-box"><div class="sol-dia-anim" style="opacity: 0.85;">🌤️</div>{nubes}</div>'
    elif tc == "nublado" or "nublado" in tc:
        nubes = "".join([f'<div class="nube-desplazandose" style="top: {(6 + i*16)}%; animation-duration: {9 + (i%4)*2}s; animation-delay: {i*1.1}s;">☁️</div>' for i in range(8)])
        return f'<div class="clima-anim-box">{nubes}</div>'
    elif "lluvioso" in tc:
        gotas = "".join([f'<div class="gota-dia" style="left: {i*6}%; animation-delay: {(i*0.07)%1}s;"></div>' for i in range(18)])
        return f'<div class="clima-anim-box">{gotas}</div>'
    elif "tormenta eléctrica" in tc:
        gotas = "".join([f'<div class="gota-dia-intensa" style="left: {i*6}%; animation-delay: {(i*0.05)%1}s;"></div>' for i in range(20)])
        return f'<div class="clima-anim-box"><div class="flash-rayo-pantalla-dia"></div>{gotas}</div>'
    elif "nevado" in tc:
        copos = "".join([f'<div class="copo-dia" style="left: {i*8}%; animation-delay: {(i*0.2)%2}s;">❄️</div>' for i in range(14)])
        return f'<div class="clima-anim-box">{copos}</div>'

    return '<div class="clima-anim-box"><div class="sol-dia-anim">☀️</div></div>'

html_animacion_actual = generar_html_animacion_fondo(cond_actual_real)
cfg = TEMAS_CLIMA_OSCURO.get(cond_actual_real, TEMAS_CLIMA_OSCURO["Nublado"])
hex_bg = cfg['bg'].lstrip('#')
r, g, b = int(hex_bg[0:2], 16), int(hex_bg[2:4], 16), int(hex_bg[4:6], 16)

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@500;700&display=swap');

    .stApp {{
        background-color: rgba({r}, {g}, {b}, 0.98) !important;
        color: {cfg['text']} !important;
        font-family: 'Quicksand', sans-serif;
    }}
    
    @media (max-width: 768px) {{
        .row-widget.stHorizontal {{ flex-direction: column !important; }}
        div[data-testid="column"] {{ width: 100% !important; flex: 100% !important; min-width: 100% !important; margin-bottom: 12px; }}
    }}

    .clima-anim-box {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        pointer-events: none; z-index: 0; overflow: hidden; margin: 0; padding: 0;
    }}

    @keyframes flashDia {{
        0%, 85%, 93%, 100% {{ background-color: rgba(255, 255, 255, 0); }}
        88%, 91% {{ background-color: rgba(255, 255, 255, 0.3); }}
    }}
    @keyframes flashNoche {{
        0%, 85%, 93%, 100% {{ background-color: rgba(0, 0, 0, 0); }}
        88%, 91% {{ background-color: rgba(232, 121, 249, 0.28); }}
    }}
    .flash-rayo-pantalla-dia {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 0; animation: flashDia 3s infinite; }}
    .flash-rayo-pantalla-noche {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 0; animation: flashNoche 2.5s infinite; }}

    @keyframes moverNubeFondo {{
        0% {{ transform: translateX(-25vw); opacity: 0; }}
        15% {{ opacity: 0.85; }}
        85% {{ opacity: 0.85; }}
        100% {{ transform: translateX(115vw); opacity: 0; }}
    }}
    .nube-desplazandose {{ position: absolute; font-size: 4.5rem; animation: moverNubeFondo linear infinite; filter: drop-shadow(0 6px 15px rgba(0,0,0,0.25)); z-index: 0; }}
    .nube-desplazandose-lenta {{ position: absolute; font-size: 4.8rem; animation: moverNubeFondo linear infinite; filter: drop-shadow(0 6px 20px rgba(189,178,255,0.2)); z-index: 0; opacity: 0.9; }}

    @keyframes brilloEstatico {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 15px {cfg['accent']}); }}
        50% {{ transform: scale(1.06); filter: drop-shadow(0 0 32px {cfg['accent']}); }}
    }}
    .sol-dia-anim {{ position: absolute; top: 7%; right: 9%; font-size: 4.8rem; animation: brilloEstatico 4s ease-in-out infinite; }}
    .luna-noche {{ position: absolute; top: 7%; right: 9%; font-size: 4.2rem; animation: brilloEstatico 4s ease-in-out infinite; }}
    
    @keyframes destelloParticula {{
        0%, 100% {{ opacity: 0.2; transform: scale(0.7); }}
        50% {{ opacity: 0.9; transform: scale(1.3); filter: drop-shadow(0 0 10px #FFB703); }}
    }}
    .particula-destello-sol {{ position: absolute; font-size: 1.4rem; animation: destelloParticula 2.5s ease-in-out infinite; }}

    @keyframes titilarEstrella {{
        0%, 100% {{ opacity: 0.2; transform: scale(0.7); }}
        50% {{ opacity: 1; transform: scale(1.3); filter: drop-shadow(0 0 8px #A0C4FF); }}
    }}
    .estrella-noche {{ position: absolute; font-size: 1.2rem; animation: titilarEstrella 2s ease-in-out infinite; }}

    @keyframes cometaCruzando {{
        0% {{ transform: translateX(-10vw) translateY(-5vh); opacity: 0; }}
        20% {{ opacity: 1; }}
        100% {{ transform: translateX(110vw) translateY(55vh); opacity: 0; }}
    }}
    .cometa-veloz-bg {{ position: absolute; top: 5%; left: -5%; width: 120px; height: 2px; background: linear-gradient(90deg, #FFFFFF, rgba(160,196,255,0)); animation: cometaCruzando 7s linear infinite; transform: rotate(-25deg); }}

    @keyframes caidaGota {{
        0% {{ transform: translateY(-20px); opacity: 0; }}
        30% {{ opacity: 0.9; }}
        100% {{ transform: translateY(100vh); opacity: 0.2; }}
    }}
    .gota-dia {{ position: absolute; width: 2px; height: 18px; background: {cfg['accent']}; animation: caidaGota 1.2s linear infinite; }}
    .gota-dia-intensa {{ position: absolute; width: 2.5px; height: 22px; background: {cfg['accent']}; animation: caidaGota 0.7s linear infinite; }}
    .gota-noche {{ position: absolute; width: 2px; height: 18px; background: #38BDF8; animation: caidaGota 1.2s linear infinite; }}
    .gota-noche-intensa {{ position: absolute; width: 2.5px; height: 22px; background: #E879F9; animation: caidaGota 0.7s linear infinite; }}

    @keyframes caidaCopo {{
        0% {{ transform: translateY(-20px) rotate(0deg); opacity: 0; }}
        30% {{ opacity: 0.9; }}
        100% {{ transform: translateY(100vh) rotate(360deg); opacity: 0.2; }}
    }}
    .copo-dia, .copo-noche {{ position: absolute; font-size: 1.2rem; animation: caidaCopo 3s linear infinite; }}

    @keyframes radarPulso {{
        0% {{ transform: scale(0.8); opacity: 0.05; }}
        50% {{ transform: scale(1.3); opacity: 0.25; }}
        100% {{ transform: scale(0.8); opacity: 0.05; }}
    }}
    .radar-nocturno {{ position: absolute; width: 500px; height: 500px; bottom: -150px; left: -150px; background: radial-gradient(circle, rgba(56,189,248,0.15) 0%, rgba(0,0,0,0) 70%); border-radius: 50%; animation: radarPulso 4s ease-in-out infinite; }}
    .nebulosa-nocturna {{ position: absolute; width: 350px; height: 350px; top: -80px; right: -80px; background: radial-gradient(circle, rgba(189,178,255,0.2) 0%, rgba(0,0,0,0) 70%); border-radius: 50%; }}
    .aura-fria {{ position: absolute; width: 100vw; height: 100vh; top: 0; left: 0; background: radial-gradient(circle at 80% 20%, rgba(144,224,239,0.1) 0%, rgba(0,0,0,0) 70%); pointer-events: none; }}

    section[data-testid="stSidebar"] {{
        background-color: {cfg['sidebar']} !important;
        border-right: 1.5px solid {cfg['accent']}33;
    }}
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] div {{
        color: {cfg['text']} !important;
    }}
    .stTextInput input, .stSelectbox select, div[data-baseweb="select"] > div {{
        color: {cfg['input_text']} !important;
        background-color: {cfg['card']} !important;
        border-color: {cfg['accent']}66 !important;
    }}
    div[data-testid="stVerticalBlock"] {{ position: relative; z-index: 1; }}

    @keyframes saltitoGatito {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-4px); }}
    }}
    .tarjeta-gatito-box {{
        background: {cfg['badge']}; border: 1.5px dashed {cfg['accent']}cc;
        border-radius: 16px; padding: 10px; text-align: center; margin: 10px 0 6px 0;
        animation: saltitoGatito 3s ease-in-out infinite;
        display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 110px;
    }}
    .gato-avatar {{
        position: relative; width: 52px; height: 40px; background: {cfg['accent']};
        border-radius: 24px 24px 16px 16px; margin: 4px auto; box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }}
    .gato-avatar .oreja {{
        position: absolute; top: -8px; width: 0; height: 0;
        border-left: 7px solid transparent; border-right: 7px solid transparent;
        border-bottom: 13px solid {cfg['accent']};
    }}
    .gato-avatar .oreja.izq {{ left: 3px; transform: rotate(-12deg); }}
    .gato-avatar .oreja.der {{ right: 3px; transform: rotate(12deg); }}
    .cara {{ position: relative; padding-top: 10px; }}
    .ojitos span {{ display: inline-block; width: 5px; height: 5px; background: #FFFFFF; border-radius: 50%; margin: 0 5px; }}
    .ojitos-durmiendo span {{ display: inline-block; width: 6px; height: 2px; background: #FFFFFF; border-radius: 2px; margin: 0 4px; }}
    .lentes-css-ojos {{ display: flex; align-items: center; justify-content: center; gap: 2px; margin: 1px auto 0 auto; }}
    .lentes-css-ojos .cristal {{ width: 14px; height: 9px; background: #111111; border-radius: 3px; }}
    .lentes-css-ojos .puente {{ width: 3px; height: 2px; background: #111111; }}
    .hocico {{ font-size: 0.65rem; color: #FFFFFF; font-weight: bold; line-height: 0.7; margin-top: 3px; }}
    .icono-clima-flotante {{ position: absolute; top: -8px; right: -10px; font-size: 1.15rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2)); }}
    .burbuja-texto {{ background: {cfg['card']}; border: 1px solid {cfg['accent']}44; border-radius: 10px; padding: 4px 8px; margin-top: 6px; width: 100%; }}
    .frase-cat {{ font-size: 0.73rem; color: {cfg['accent']}; font-weight: 700; display: block; }}

    .tarjeta-clima-custom {{
        background: {cfg['card']}; border: 2px solid {cfg['accent']}66;
        border-radius: 20px; padding: 16px 10px; text-align: center;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08); margin-bottom: 10px;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }}
    .tarjeta-clima-custom:hover {{ transform: translateY(-8px); border-color: {cfg['accent']}; }}
    .fecha-tarjeta {{ color: {cfg['accent']}; font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; }}
    .temp-tarjeta {{ color: {cfg['val_color']}; font-size: 1.9rem; font-weight: 700; line-height: 1.1; margin-bottom: 6px; }}
    .min-tarjeta {{ background-color: {cfg['badge']}; color: {cfg['text']}; border-radius: 10px; padding: 3px 10px; display: inline-block; font-size: 0.78rem; font-weight: 700; border: 1px solid {cfg['accent']}44; margin-bottom: 4px; }}
    .extra-detalles {{ font-size: 0.73rem; color: {cfg['subtext']}; font-weight: 600; margin-top: 4px; }}

    .tarjeta-hora-custom {{
        background: {cfg['card']}; border: 1.5px solid {cfg['accent']}44;
        border-radius: 14px; padding: 8px 4px; text-align: center; margin-bottom: 8px;
    }}
    .hora-txt {{ color: {cfg['accent']}; font-size: 0.8rem; font-weight: 700; margin-bottom: 2px; }}
    .temp-hora-txt {{ color: {cfg['val_color']}; font-size: 1.1rem; font-weight: 700; margin-bottom: 2px; }}

    h1, h2, h3, h4 {{ color: {cfg['accent']} !important; text-align: center; font-weight: 700; }}
    .stButton>button {{
        background-color: {cfg['card']} !important; color: {cfg['accent']} !important;
        border: 2px solid {cfg['accent']}88 !important; border-radius: 12px !important; font-weight: 700 !important;
    }}
    .stButton>button:hover {{ background-color: {cfg['accent']} !important; color: #FFFFFF !important; }}
    </style>

    {html_animacion_actual}
""", unsafe_allow_html=True)

if st.session_state.vista_museo:
    if st.button("⬅️ Volver al inicio"):
        st.session_state.vista_museo = False
        st.rerun()

    st.title("Museo de Gatitos del Clima")
    climas_museo = [
        "Soleado", "Parcialmente nublado", "Nublado", "Lluvioso", "Tormenta eléctrica", "Nevado",
        "Noche despejada", "Noche parcialmente nublada", "Noche nublada", "Noche lluviosa", "Tormenta eléctrica nocturna", "Noche nevada"
    ]
    cols_museo = st.columns(3)
    for idx, c_m in enumerate(climas_museo):
        with cols_museo[idx % 3]:
            st.markdown(f"<h4>{c_m}</h4>", unsafe_allow_html=True)
            st.markdown(obtener_gatito_segun_clima(c_m), unsafe_allow_html=True)

elif not st.session_state.vista_detalle:
    st.title(f"Clima Bonito • {municipio_limpio}, {estado_limpio}")
    simbolo_temp = st.session_state.unidades_temp
    st.markdown(f"<p style='text-align: center; font-size: 1.15rem; font-weight: 600;'>Ambiente actual: <b style='color: {cfg['accent']};'>{cond_actual_real}</b> {icono_actual_real} | Unidades: {simbolo_temp}</p>", unsafe_allow_html=True)

    cols = st.columns(4)
    for idx, row in df_p.iterrows():
        with cols[idx]:
            st.markdown(f"""
                <div class="tarjeta-clima-custom">
                    <div class="fecha-tarjeta">{row['FechaTitulo']}</div>
                    <div class="temp-tarjeta">{row['TMAX']}{simbolo_temp}</div>
                    <div class="min-tarjeta">Mín: {row['TMIN']}{simbolo_temp}</div>
                    <div class="extra-detalles">💧 Hum.: {row['Humedad']}%<br>☀️ UV: {row['UV']}</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center;'><span style='background-color: {cfg['badge']}; color: {cfg['accent']}; padding: 3px 8px; border-radius: 12px; font-size: 0.78rem; font-weight: bold;'>{row['Icono']} {row['Tipo']}</span></div>", unsafe_allow_html=True)
            st.markdown(row["GatitoHtml"], unsafe_allow_html=True)
            if st.button("📊 Ver detalle", key=f"btn_{row['ID']}", use_container_width=True):
                st.session_state.dia_seleccionado = row["ID"]
                st.session_state.vista_detalle = True
                st.rerun()

else:
    dia_actual_info = df_p[df_p["ID"] == st.session_state.dia_seleccionado].iloc[0]
    simbolo_temp = st.session_state.unidades_temp

    if st.button("⬅️ Volver al inicio"):
        st.session_state.vista_detalle = False
        st.rerun()

    st.title(f"Detalle del Clima • {dia_actual_info['FechaTitulo']}")
    st.markdown(f"<p style='text-align: center; color: {cfg['accent']}; font-size: 1.2rem; font-weight: 700;'>Máxima: <b>{dia_actual_info['TMAX']}{simbolo_temp}</b> | Mínima: <b>{dia_actual_info['TMIN']}{simbolo_temp}</b> {dia_actual_info['Icono']}</p>", unsafe_allow_html=True)

    t_max_sel, t_min_sel = dia_actual_info["TMAX"], dia_actual_info["TMIN"]
    horas, temps, iconos_horas, desc_horas = [], [], [], []

    if datos_api_raw and "hourly" in datos_api_raw and "weathercode" in datos_api_raw["hourly"]:
        try:
            dia_idx = st.session_state.dia_seleccionado
            inicio_hr, fin_hr = dia_idx * 24 + 6, dia_idx * 24 + 24
            temps_hora_api = datos_api_raw["hourly"]["temperature_2m"][inicio_hr:fin_hr]
            codes_hora_api = datos_api_raw["hourly"]["weathercode"][inicio_hr:fin_hr]
            for idx_h, h in enumerate(range(6, 24)):
                horas.append(f"{h:02d}:00")
                t_val = temps_hora_api[idx_h] if idx_h < len(temps_hora_api) else t_min_sel
                temps.append(convertir_temp(t_val))
                c_val = codes_hora_api[idx_h] if idx_h < len(codes_hora_api) else 0
                cond_h, icon_h = interpretar_weathercode(c_val, hora=h, minuto=0)
                iconos_horas.append(icon_h)
                desc_horas.append(f"{icon_h} {cond_h}")
        except Exception:
            for h in range(6, 24):
                factor = abs(math.sin(math.pi * (h - 6) / 16))
                temps.append(round(t_min_sel + factor * (t_max_sel - t_min_sel), 1))
                horas.append(f"{h:02d}:00")
                iconos_horas.append(dia_actual_info["Icono"])
                desc_horas.append(f"{dia_actual_info['Icono']} {dia_actual_info['Tipo']}")
    else:
        for h in range(6, 24):
            factor = abs(math.sin(math.pi * (h - 6) / 16))
            temps.append(round(t_min_sel + factor * (t_max_sel - t_min_sel), 1))
            horas.append(f"{h:02d}:00")
            iconos_horas.append(dia_actual_info["Icono"])
            desc_horas.append(f"{dia_actual_info['Icono']} {dia_actual_info['Tipo']}")

    df_horas = pd.DataFrame({"Hora":horas, f"Temperatura ({simbolo_temp})":temps, "Icono":iconos_horas, "Condicion":desc_horas})

    fig = px.area(df_horas, x="Hora", y=f"Temperatura ({simbolo_temp})", markers=True, line_shape="spline")
    fig.update_traces(line=dict(color=cfg["accent"], width=3), marker=dict(size=7, color=cfg["accent"]), fill="tozeroy", fillcolor=f"{cfg['accent']}33")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Quicksand", color=cfg["text"], size=12), height=280, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    cols_horas = st.columns(6)
    for idx_h, row_h in df_horas.iterrows():
        with cols_horas[idx_h % 6]:
            st.markdown(f"""
                <div class="tarjeta-hora-custom">
                    <div class="hora-txt">{row_h['Hora']}</div>
                    <div class="temp-hora-txt">{row_h[f'Temperatura ({simbolo_temp})']}{simbolo_temp}</div>
                    <div style="font-size: 0.65rem; color: {cfg['subtext']};">{row_h['Condicion']}</div>
                </div>
            """, unsafe_allow_html=True)
