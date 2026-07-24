import pandas as pd
import numpy as np
import geopandas as gpd
import streamlit as st
import folium
import json
from folium import Element
from numpy import float64
import matplotlib.pyplot as plt
from streamlit_folium import st_folium

@st.cache_data
def load_initial_data(selectedcantons):
    """Lädt Basis-Daten (wird nur einmal geladen!)"""
    data_toml = json.loads(st.secrets["my_data"]["data"])
    data = pd.DataFrame(data_toml)
    invalid_gemeinden = [2016, 2520, 700, 2027, 2529, 2278, 4122]
    data = data[(data['Kanton'].isin(selectedcantons))&(~data['BFS Gde-nummer'].isin(invalid_gemeinden))].reset_index(drop=True)
    return data

@st.cache_data
def load_gemeinden2d(selectedcantons):
    """Lädt GeoDataFrame (wird nur einmal heruntergeladen!)"""
    gemeinden2d = gpd.read_file('https://raw.githubusercontent.com/mstorange/gemeinderating_open_fullCH/main/Gemeinden2D_2026.gpkg')
    gemeinden2d = gemeinden2d[(gemeinden2d['kanton'].isin(selectedcantons))&(gemeinden2d['bfs_nummer']!=0)].reset_index(drop=True)
    return gemeinden2d[['bfs_nummer', 'name','einwohnerzahl', 'geometry']]

@st.cache_data
def normalize_column_vectorized(series, invert=False):
    """Schnelle vektorisierte Normalisierung (NICHT in Loops!)"""
    vmin = series.min()
    vmax = series.max()
    if vmax == vmin:
        return pd.Series([0.5] * len(series), index=series.index)
    normalized = (series - vmin) / (vmax - vmin)
    return 1 - normalized if invert else normalized

# ⭐ HILFSFUNKTION für Hex-Farbe
def rgba_to_hex(rgba):
    """Konvertiert RGBA zu Hex"""
    return '#{:02x}{:02x}{:02x}'.format(int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))

def wide_space_default():
    st.set_page_config(layout='wide')
wide_space_default()

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if check_password():
    
    st.title('Gemeinderating von CAJ/MST')
    st.write('Die Karte gibt erste Anhaltspunkte zur Attraktivität einer Gemeinde aus Investorenperspektive. Alle Gemeinden der ausgewählten Kantone werden hierzu miteinander verglichen. Als Datenbasis gelten WP-Daten sowie die im Herbst 2025 publizierte Studie von Urbanistica & Sotomo zum Innenentwicklungspotenzial von Schweizer Gemeinden. Wie immer sind diese Daten mit Vorsicht zu geniessen, weil wir nicht wissen, wie sie erhoben und prozessiert wurden.')
    
    # --- session state init ---
    if "applied" not in st.session_state:
        st.session_state.applied = False
    
    
    
    #allurls = ["https://raw.githubusercontent.com/mstorange/gemeinderating/main/AG.csv", "https://raw.githubusercontent.com/mstorange/gemeinderating/main/TG_SG.csv", "https://raw.githubusercontent.com/mstorange/gemeinderating/main/ZG_LU.csv"]
    
    #for file in allurls:
        #df = pd.read_csv(file)
        #data = pd.concat([data, df], ignore_index=True)

    # nur jene Kantone, wovon mehrere Gemeinden vorkommen

    
    valid_kantone = ["AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "JU", 
    "LU", "NE", "NW", "OW", "SG", "SH", "SO", "SZ", "TG", "UR", 
    "VD", "VS", "ZG", "ZH"]
    
    #print('Anzahl valide Gemeinden mit Geometrien: ', len(data))
        #st.write('Länge des merges:', len(storedf_geo))
        #st.write('Hier gemeinden2d.empty testen:', gemeinden2d.empty)
    #storedf_geo = gpd.GeoDataFrame(storedf_geo, crs='EPSG:2056', geometry='geometry')
    
    
    with st.form("filter_form"):
        selected_cantons = st.multiselect(
            "Kantone auswählen",
            valid_kantone
        )
        

        st.write("Gewichte selbst definieren. Falls nichts geändert, wird LM-Gewichtung genommen, falls Gewicht 0 -> Kriterium wird ignoriert.")
        with st.expander("Gewichte aufklappen", expanded=False):
            g_0 = st.number_input("Wohnpreis Miete 70%-Q: ", value=1.5, placeholder="Default: 1.5")
            #g_1 = st.number_input("Wohnpreis (Region): ", value=1, placeholder="Default: 1")
            g_2 = st.number_input("Wohnpreis (Entwicklung): ", value=1.25, placeholder="Default: 1.25")
            g_2b = st.number_input("STWE-Preis (aktuell): ", value=1, placeholder="Default: 1")
            g_2c = st.number_input("STWE-Preis (Entwicklung): ", value=1, placeholder="Default: 1")
            g_3 = st.number_input("Baulandpreis (aktuell): ", value=1.5, placeholder="Default: 1.5")
            g_4 = st.number_input("Baulandpreis (Entwicklung): ", value=1, placeholder="Default: 1")
            g_5 = st.number_input("Bevölkerung (Prognose): ", value=1.25, placeholder="Default: 1.25")
            g_6 = st.number_input("Alterung (Prognose): ", value=1, placeholder="Default: 1")
            g_7 = st.number_input("Beschäftigte (Prognose): ", value=1, placeholder="Default: 1")
            g_8 = st.number_input("Erreichbarkeit ÖV: ", value=1.25, placeholder="Default: 1.25")
            g_9 = st.number_input("Erreichbartkeit MIV: ", value=1.25, placeholder="Default: 1.25")
            g_10 = st.number_input("Innenentwicklungspotenzial: ", value=1, placeholder="Default: 1")
            #g_11 = st.number_input("Steuern DINKs: ", value=1, placeholder="Default: 1")

        with st.expander("Filter setzen (bspw. nur alle Gemeinden mit Mietpreisen > 250 CHF/m2 einblenden)", expanded=False):
            # Werte aus WP-Berichte_App.ipynb vom concat der Kantone SG, TG, LU, ZG, AG
            slider_miete1 = st.slider(label="Mietzins (70%-Q.)", min_value=135, max_value=562, step=10, value=(135, 562))
            #slider_miete2 = st.slider(label="Mietzins-Verhältnis vgl. zu Region min (70%-Q.)", min_value=data['Wohnpreis (vgl. Region)'].min()-0.1, max_value=data['Wohnpreis (vgl. Region)'].max()+0.1, step=0.1, value=(data['Wohnpreis (vgl. Region)'].min()-0.1, data['Wohnpreis (vgl. Region)'].max()+0.1))
            slider_miete3 = st.slider(label="Mietzins-Entwicklung seit 2021 (70%-Q.)", min_value=-13.3, max_value=107.9, step=0.1, value=(-13.3, 107.9))
            slider_stwe1= st.slider(label="STWE-Preis (70%-Q.)", min_value=3052, max_value=25260, step=10, value=(3052, 25260))
            slider_stwe2 = st.slider(label="STWE-Entwicklung seit 2021 (70%-Q.)", min_value=-21.7, max_value=158.3, step=0.1, value=(-21.7, 158.3))
            slider_land1 = st.slider(label="Baulandpreis (mittlere Lage)", min_value=50, max_value=9650, step=50, value=(50, 9650))
            slider_land2 = st.slider(label="Baulandpreis-Entwicklung (Verhältnis zu 2019, mittlere Lage)", min_value=-60.9, max_value=138.3, step=0.1, value=(-60.9, 138.3))
            slider_bev = st.slider(label="Bevölkerung Prognose (Verhältnis 2024 zu 2035)", min_value=-0.2, max_value=0.7, step=10.0, value=(-0.2, 0.7))
            slider_alterung = st.slider(label="Alterung Prognose (Anteil Ü65, Verhältnis 2024 zu 2035)", min_value=-0.3, max_value=2.0, step=0.1, value=(-0.3, 2.0))
            slider_beschäftigte = st.slider(label="Beschäftigte Prognose (Verhältnis 2024 zu 2035)", min_value=-0.38, max_value=0.97, step=0.1, value=(-0.38, 0.97))
            slider_err_öv = st.slider(label="Erreichbarkeit Personen & Beschäftigte ÖV (30 Min.-Umkreis)", min_value=50, max_value=2050000, step=10000, value=(50, 2050000))
            slider_err_miv = st.slider(label="Erreichbarkeit Pesonen & Beschäftigte MIV (30 Min.-Umkreis)", min_value=4600, max_value=3850000, step=100000, value=(4600, 3850000))
            #slider_steuern = st.slider(label="Steuern DINKs (Mittelwert über alle Einkommensklassen)", min_value=data['Steuern_DINKs          '].min()-0.05, max_value=data['Steuern_DINKs          '].max()+0.05, step=0.05, value=(data['Steuern_DINKs          '].min()-0.05, data['Steuern_DINKs          '].max()+0.05))
            slider_innen = st.slider(label="Innenentwicklungspotenzial (Sotomo/Urbanistica)", min_value=0.0, max_value=4.1, step=0.1, value=(0.0, 4.1))
    
        submitted = st.form_submit_button("Anwenden")
    
    if submitted:
        st.session_state.applied = True
        st.session_state.selected_cantons = selected_cantons
    
        st.write("Folgende Kantone werden analysiert:", ', '.join(selected_cantons))
        #st.write("Typ der selected_cantons variable:", type(selected_cantons))
        fd = load_initial_data(selectedcantons = st.session_state.selected_cantons)  # Lädt gecacht!
        #fd = data[data["Kanton"].isin(st.session_state.selected_cantons)].reset_index(drop=True)

        # für die Slider: absolute Werte ergänzen
        fd['Mietpreis (70%-Q)'] = fd['Wohnpreis (aktuell)    ']*1
        #fd['Baulandpreis (50%-Q)'] = fd['Baulandpreis (aktuell) ']*1
        #fd['Wohnpreis Miete vgl. zu Region (70%-Q)'] = fd['Wohnpreis (vgl. Region)']*1
        fd['Mietpreis-Entwicklung seit 2021 (70%-Q)'] = fd['Wohnpreis (Entwicklung)']*1
        fd['STWE-Preis (70%-Q)'] = fd['STWE-Preis (aktuell)   ']*1
        fd['STWE-Entwicklung seit 2021 (70%-Q)'] = fd['STWE-Preis (Entw.)     ']*1
        fd['Baulandpreis aktuell (mittlere Lage)'] = fd['Baulandpreis (aktuell) ']*1
        fd['Baulandpreis-Entwicklung seit 2019'] = fd['Baulandpreis (Entw.)   ']*1
        fd['Bevölkerung Prognose bis 2035'] = fd['Bevölkerung (Prognose) ']*1
        fd['Alterung Prognose bis 2035 (Anteil Ü65)'] = fd['Alterung (Prognose)    ']*1
        fd['Beschäftigte Prognose bis 2035'] = fd['Beschäftigte (Prognose)']*1
        fd['Erreichbarkeit ÖV (30 Min.)'] = fd['Erreichbarkeit ÖV      ']*1
        fd['Erreichbarkeit MIV (30 Min.)'] = fd['Erreichbarkeit MIV     ']*1
        #fd['Steuern DINKs (Avg. Einkommen)'] = fd['Steuern_DINKs          ']*1
        fd['Innenentwicklungspotenzial Sotomo/Urbanistica'] = fd['Innenentw.-potenzial   ']*1

        # wenn wir die slider hier anwenden, dann werden zuerst die Dinge rausgeworfen und dann die verbleibenden miteinander verglichen -> wollen wir nicht
        # fd = fd[fd['Wohnpreis (Miete, 70%-Q)']>=slider_miete1].reset_index(drop=True)

        # ⭐ ERSETZE ALLES DURCH:
        fd['Wohnpreis (aktuell)    '] = normalize_column_vectorized(fd['Wohnpreis (aktuell)    '], invert=False)
        fd['Wohnpreis (Entwicklung)'] = normalize_column_vectorized(fd['Wohnpreis (Entwicklung)'], invert=False)
        fd['STWE-Preis (aktuell)   '] = normalize_column_vectorized(fd['STWE-Preis (aktuell)   '], invert=False)
        fd['STWE-Preis (Entw.)     '] = normalize_column_vectorized(fd['STWE-Preis (Entw.)     '], invert=False)
        fd['Baulandpreis (aktuell) '] = normalize_column_vectorized(fd['Baulandpreis (aktuell) '], invert=True)  # invert=True!
        fd['Baulandpreis (Entw.)   '] = normalize_column_vectorized(fd['Baulandpreis (Entw.)   '], invert=True)
        fd['Bevölkerung (Prognose) '] = normalize_column_vectorized(fd['Bevölkerung (Prognose) '], invert=False)
        fd['Alterung (Prognose)    '] = normalize_column_vectorized(fd['Alterung (Prognose)    '], invert=True)
        fd['Beschäftigte (Prognose)'] = normalize_column_vectorized(fd['Beschäftigte (Prognose)'], invert=False)
        fd['Erreichbarkeit ÖV      '] = normalize_column_vectorized(fd['Erreichbarkeit ÖV      '], invert=False)
        fd['Erreichbarkeit MIV     '] = normalize_column_vectorized(fd['Erreichbarkeit MIV     '], invert=False)
        fd['Innenentw.-potenzial   '] = normalize_column_vectorized(fd['Innenentw.-potenzial   '], invert=False)
        
        # Summe
        
        kriterien = ['Wohnpreis (aktuell)    ', 'Wohnpreis (Entwicklung)', 'STWE-Preis (aktuell)   ',  'STWE-Preis (Entw.)     ',
               'Baulandpreis (aktuell) ', 'Baulandpreis (Entw.)   ',
               'Bevölkerung (Prognose) ', 'Alterung (Prognose)    ',
               'Beschäftigte (Prognose)', 'Erreichbarkeit ÖV      ',
               'Erreichbarkeit MIV     ',
               'Innenentw.-potenzial   ']
        # Gewichte festlegen: das ist hier ist der Standard LM
        #g = [1.5, 1, 1.25, 1.5, 1, 1.25, 1, 1, 1.25, 1.25, 1, 1]

        
        fd['Summe1'] = g_0*fd['Wohnpreis (aktuell)    ']+g_2*fd['Wohnpreis (Entwicklung)']+g_2b*fd['STWE-Preis (aktuell)   ']+g_2c*fd['STWE-Preis (Entw.)     ']+g_3*fd['Baulandpreis (aktuell) ']+g_4*fd['Baulandpreis (Entw.)   ']+g_5*fd['Bevölkerung (Prognose) ']+g_6*fd['Alterung (Prognose)    ']+g_7*fd['Beschäftigte (Prognose)']+g_8*fd['Erreichbarkeit ÖV      ']+g_9*fd['Erreichbarkeit MIV     ']+g_10*fd['Innenentw.-potenzial   ']
        # hier auf keinen Fall sortieren, weil sonst Dataframe ergänzgen falsch wird fd = fd.sort_values(by='Gemeinde', ascending=True)
        fd = fd.round(2)
        
        
        gemeinden2d = load_gemeinden2d(selectedcantons = st.session_state.selected_cantons)  # Lädt gecacht!

        ##st.write('Welche Spalten hat gemeinden2d?')
        #st.write(gemeinden2d.columns)
        #st.write('Welche Spalten hat fd?')
        #st.write(fd.columns)
        
        # Gemeindegeometrien dazufügen
        storedf_geo = fd.merge(right=gemeinden2d, left_on='Gemeindename',right_on='name', how='left')
        #st.write('Länge des merges:', len(storedf_geo))
        #st.write('Hier gemeinden2d.empty testen:', gemeinden2d.empty)
        storedf_geo = gpd.GeoDataFrame(storedf_geo, crs='EPSG:2056', geometry='geometry')

        
        # critical for streamlit
        # storedf_geo = storedf_geo[storedf_geo.geometry.notna()].copy()
        
        #st.write('Check if no rows...')
        #if storedf_geo.empty:
            #st.error("Keine gültigen Geometrien nach dem Merge gefunden.")
            #st.stop()
        
        
        norm = plt.Normalize(storedf_geo['Summe1'].min(), storedf_geo['Summe1'].max())
        cmap = plt.get_cmap('RdYlGn')
        def rgba_to_hex(rgba):
            return '#{:02x}{:02x}{:02x}'.format(int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))
        # farben zum gdf dazufügen
        storedf_geo['farbe'] = storedf_geo['Summe1'].apply(lambda x: cmap(norm(x)))
        storedf_geo.tail(1)
        # storedf_geo['farbe'] = storedf_geo['farbe'].apply(lambda x: f'rgba{x}')
        storedf_geo['farbe'] = storedf_geo['farbe'].apply(lambda x: rgba_to_hex(x))
        
        
        relcols = ['Wohnpreis (aktuell)    ', 'Wohnpreis (Entwicklung)', 'STWE-Preis (aktuell)   ',  'STWE-Preis (Entw.)     ',
               'Baulandpreis (aktuell) ', 'Baulandpreis (Entw.)   ',
               'Bevölkerung (Prognose) ', 'Alterung (Prognose)    ',
               'Beschäftigte (Prognose)', 'Erreichbarkeit ÖV      ',
               'Erreichbarkeit MIV     ',
               'Innenentw.-potenzial   ']
        
        for colname in relcols:
               norm = plt.Normalize(storedf_geo[colname].min(), storedf_geo[colname].max())
               cmap = plt.get_cmap('RdYlGn')
               # farben zum gdf dazufügen
               farbcolname = 'farbe'+colname
               storedf_geo[farbcolname] = storedf_geo[colname].apply(lambda x: cmap(norm(x)))
               storedf_geo.tail(1)
               # storedf_geo['farbe'] = storedf_geo['farbe'].apply(lambda x: f'rgba{x}')
               storedf_geo[farbcolname] = storedf_geo[farbcolname].apply(lambda x: rgba_to_hex(x))
        
        # über alle columns ein html bauen
        
        for c in relcols:
            print('column: ', c)
            # newcolname = c+'_html'
            def range_indicator(row):
                spalte = c
                wert = row[c]
                return f"""
                <div style='font-family:Arial; font-size:12px;display:flex; align-items:left;'>
                    <div style='width:200px;'><strong>{spalte}:</strong> {wert:.2f}</div>
                    <div style='position:relative; height:10px; background:#eee; width:100px; display:inline-block; margin-left:5px;'>
                        <div style='position:absolute; left:{wert*100:.0f}px; top:0; width:2px; height:10px; background:#4888e8;'></div>
                    </div>
                </div>
                """
            storedf_geo[c] =storedf_geo.apply(range_indicator, axis=1)
        
        
        # zusätzlich noch für die Summe ein eigenes html bauen
        summax = storedf_geo.Summe1.max()
        summin = storedf_geo.Summe1.min()
        
        def sum_indicator_sum(row):
            summe = row['Summe1']
            farbe = row['farbe']
            summe_normalized = (summe-summin)/(summax-summin) # brauchen wir, damit der Summenwert auch auf derselben Skala dargestellt werden kann, der Wert soll jedoch als unnormalisierte Zahl dargestellt werden
            return f"""
                <div style='font-family:Arial; font-size:12px;display:flex; align-items:left;'>
                    <div style='width:200px;'><strong>Summe:</strong> {summe:.2f}</div>
                    <div style='position:relative; height:10px; background:#eee; width:100px; display:inline-block; margin-left:5px;'>
                        <div style='position:absolute; left:{summe_normalized*100:.0f}px; top:0; width:2px; height:10px; background:#e33474;'></div>
                    </div>
                </div>
                """
        
        storedf_geo['Summe'] =storedf_geo.apply(sum_indicator_sum, axis=1)
        
        for col in relcols:
            # print(col)
            # print(storedf_geo[col].dtype)
            if storedf_geo[col].dtype == 'float64':
                print(col)
                storedf_geo[col] = storedf_geo[col].astype(str)
        
        
        storedf_geo = storedf_geo.round(2)
        df = storedf_geo.to_crs(epsg=4326)

        # filter nun anwenden --> hier weiter machen nach dem Mittag

       
        
        #df = df[df['Wohnpreis (Miete, 70%-Q)']>=slider_miete1].reset_index(drop=True)
        df = df[(df['Mietpreis (70%-Q)']>=slider_miete1[0])&(df['Mietpreis (70%-Q)']<=slider_miete1[1])].reset_index(drop=True)
        #df = df[df['Wohnpreis Miete vgl. zu Region (70%-Q)']>=slider_miete2].reset_index(drop=True)
        #df = df[(df['Wohnpreis Miete vgl. zu Region (70%-Q)']>=slider_miete2[0])&(df['Wohnpreis Miete vgl. zu Region (70%-Q)']<=slider_miete2[1])].reset_index(drop=True)
        #df = df[df['Wohnpreis Entwicklung seit 2023 (70%-Q)']>=slider_miete3].reset_index(drop=True)
        df = df[(df['Mietpreis-Entwicklung seit 2021 (70%-Q)']>=slider_miete3[0])&(df['Mietpreis-Entwicklung seit 2021 (70%-Q)']<=slider_miete3[1])].reset_index(drop=True)
        df = df[(df['STWE-Preis (70%-Q)']>=slider_stwe1[0])&(df['STWE-Preis (70%-Q)']<=slider_stwe1[1])].reset_index(drop=True)
        df = df[(df['STWE-Entwicklung seit 2021 (70%-Q)']>=slider_stwe2[0])&(df['STWE-Entwicklung seit 2021 (70%-Q)']<=slider_stwe2[1])].reset_index(drop=True)
        #df = df[df['Baulandpreis aktuell (50%-Q)']<=slider_land1]
        df = df[(df['Baulandpreis aktuell (mittlere Lage)']>=slider_land1[0])&(df['Baulandpreis aktuell (mittlere Lage)']<=slider_land1[1])].reset_index(drop=True)
        #df = df[df['Baulandpreis Entwicklung seit 2020']<=slider_land2]
        df = df[(df['Baulandpreis-Entwicklung seit 2019']>=slider_land2[0])&(df['Baulandpreis-Entwicklung seit 2019']<=slider_land2[1])].reset_index(drop=True)
        df = df[(df['Bevölkerung Prognose bis 2035']>=slider_bev[0])&(df['Bevölkerung Prognose bis 2035']<=slider_bev[1])].reset_index(drop=True)
        df = df[(df['Alterung Prognose bis 2035 (Anteil Ü65)']>=slider_alterung[0])&(df['Alterung Prognose bis 2035 (Anteil Ü65)']<=slider_alterung[1])].reset_index(drop=True)
        df = df[(df['Beschäftigte Prognose bis 2035']>=slider_beschäftigte[0])&(df['Beschäftigte Prognose bis 2035']<=slider_beschäftigte[1])].reset_index(drop=True)
        df = df[(df['Erreichbarkeit ÖV (30 Min.)']>=slider_err_öv[0])&(df['Erreichbarkeit ÖV (30 Min.)']<=slider_err_öv[1])].reset_index(drop=True)
        df = df[(df['Erreichbarkeit MIV (30 Min.)']>=slider_err_miv[0])&(df['Erreichbarkeit MIV (30 Min.)']<=slider_err_miv[1])].reset_index(drop=True)
        #df = df[(df['Steuern DINKs (Avg. Einkommen)']>=slider_steuern[0])&(df['Steuern DINKs (Avg. Einkommen)']<=slider_steuern[1])].reset_index(drop=True)
        df = df[(df['Innenentwicklungspotenzial Sotomo/Urbanistica']>=slider_innen[0])&(df['Innenentwicklungspotenzial Sotomo/Urbanistica']<=slider_innen[1])].reset_index(drop=True)
        
    
        firstobject = df['geometry'][0].centroid
        
        
        
        #st.write('Folgende columns sind jetzt in df')
        #st.write(df.columns)
        
        #st.write('Hier unmittelbar vor folium.Map')
        
        satellite = folium.TileLayer(
                tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr = 'Esri',
                name = 'Esri Satellite',
                overlay = False,
                control = True)
        
        m = folium.Map(location=[firstobject.y, firstobject.x], zoom_start=10, tiles=satellite, zoom_control=False) # CartoDB dark_matter, positron, voyager
        
        
        hoverinfo = folium.GeoJsonTooltip(fields=['name','einwohnerzahl','Mietpreis (70%-Q)', 'Baulandpreis aktuell (mittlere Lage)', 'Summe1'], aliases=['Gemeinde','Einwohner 2025','Mietpreis (70%-Q)', 'Baulandpreis aktuell (mittlere Lage)', 'Rating'])
        htmlpopup = folium.GeoJsonPopup(fields=['Gemeindename','Wohnpreis (aktuell)    ', 'Wohnpreis (Entwicklung)', 'STWE-Preis (aktuell)   ',  'STWE-Preis (Entw.)     ',
               'Baulandpreis (aktuell) ', 'Baulandpreis (Entw.)   ',
               'Bevölkerung (Prognose) ', 'Alterung (Prognose)    ',
               'Beschäftigte (Prognose)', 'Erreichbarkeit ÖV      ',
               'Erreichbarkeit MIV     ',
               'Innenentw.-potenzial   ', 'Summe'], aliases=['Gemeinde', 'Mietpreis (70%-Q)','Mietpreis (Entwicklung)', 'STWE-Preis (aktuell)', 'STWE-Preis (Entwicklung)', 'Baulandpreis aktuell (mittlere Lage)', 'Baulandpreis (Entwicklung)', 'Bevölkerung (Prognose)','Alterung (Prognose)', 'Beschäftigung (Prognose)', 'Erreichbarkeit ÖV', 'Erreichbarkeit MIV', 'Innenentwicklung', 'Rating (Summe)'], labels=False, style="font-size:12px;", max_width=1200)
        
        
        # alles zusammen plotten
        fg_gemeinden = folium.FeatureGroup(name='Gemeinderating', show=True).add_to(m)
        folium.GeoJson(data=df, zoom_on_click=False, 
                style_function=lambda feature: {
                "fillColor": feature['properties']['farbe'],
                "fillOpacity":0.85,
                "color": None,
                "weight": 0.2,
                #"dashArray": "2, 2",
                },
                highlight_function=lambda feature: {
                "fillColor": feature['properties']['farbe'],
                "fillOpacity": 1
                },
            popup=htmlpopup,
            tooltip=hoverinfo, 
            popup_keep_highlighted=True
            ).add_to(fg_gemeinden)
        
        # in der Karte direkt den Gemeindenamen und den Wert anzeigen
        fg_summe_marker = folium.FeatureGroup(name='Attraktivität Summe', show=True).add_to(m)
        for _, row in df.iterrows(): # _ is a convention to tell the user that we don't need this value and it's only there since iterrow requires such a value
            name = row['Gemeindename']
            if pd.isna(row['geometry']):
                print(name)
            centroid = row['geometry'].centroid
            value = row['Summe1']
            folium.Marker(
                location=[centroid.y, centroid.x],
                icon=folium.DivIcon(html=f'<div style="font-size: 9px; color: white;">{name}<br>{value}</div>')
            ).add_to(fg_summe_marker)
        
        # pro Kriterium mit entsprechender Farbe plotten
        for columnname in relcols:
            # alles zusammen plotten
          farbcolumn = 'farbe'+columnname
          print(f"==>> farbcolumn: {farbcolumn}")
          # fg_einzelkriterium = folium.FeatureGroup(name=columnname, show=False).add_to(m)
          folium.GeoJson(data=df, zoom_on_click=False, 
                  style_function=lambda feature, fc=farbcolumn:{ # dieses fc=farbcolumn macht klar, dass immer die Farbe des entsprechenden loop elements übernommen wird (sonst wäre es late bound)
                  "fillColor": feature['properties'][fc],
                  "fillOpacity":0.85,
                  "color": None,
                  "weight": 0.2,
                  #"dashArray": "2, 2",
                  },
              # popup=htmlpopup,
              tooltip=folium.GeoJsonTooltip(fields=['Gemeindename',columnname]), 
              # popup_keep_highlighted=True
              ).add_to(folium.FeatureGroup(name=columnname, show=False).add_to(m))
          
        # fg_einzelkriterium = folium.FeatureGroup(name='ÖV Erreichbarkeit', show=True).add_to(m)
        # folium.GeoJson(data=df, zoom_on_click=False, 
        #         style_function=lambda feature: {
        #         "fillColor": feature['properties']['farbeErreichbarkeit ÖV      '],
        #         "fillOpacity":0.85,
        #         "color": None,
        #         "weight": 0.2,
        #         #"dashArray": "2, 2",
        #         },
        #     # popup=htmlpopup,
        #     tooltip=folium.GeoJsonTooltip(fields=['Erreichbarkeit ÖV      '], aliases=['Erreichbarkeit ÖV']), 
        #     # popup_keep_highlighted=True
        #     ).add_to(fg_einzelkriterium)
        
        
        
        text_box_html = '''
        <div style="
            position: fixed; 
            bottom: 10px; 
            left: 10px; 
            width: 150px; 
            height: auto; 
            padding: 10px;
            background-color: white; 
            border-radius: 0px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            font-family: Arial;
            font-size: 9px;
            font-color: black;
            z-index: 1000;
        ">
            <h1 style="margin-top: 0;font-size:12px">Erklärung</h1>
            <p>Rating ist die ungewichtete Summe aus folgenden Aspekten:<br> Wohnpreise, Wohnpreise im Vgl. zur Region, Wohnpreisentwicklung, Baulandpreise, Baulandpreisentwicklung, Bevölkerungsprognose, Alterungsprognose, Beschäftigungsprognose, Erreichbarkeit, Steuern (double income no kids) Innenentwicklungspotenzial laut Urbanistica/Sotomo(2025)<br><br>Achtung: Werte jeweils zwischen 0 und 1, wobei hier nur die dargestellten Orte untereinander verglichen werden.</p>
        </div>
        '''
        
        title_html = '''
             <h3 align="center" style="font-size:20px"><b>Gemeinderating Ostschweiz (CAJ/MST)</b></h3>
             '''
        
        m.get_root().html.add_child(Element(title_html))
        # m.get_root().html.add_child(Element(text_box_html))
        
        
        folium.TileLayer('CartoDB voyager', name= 'Karte hell').add_to(m)
        folium.TileLayer('CartoDB dark_matter', name = 'Karte dunkel').add_to(m)
        
        
        info_button_html = """
        <div id="infoButton" style="position: fixed; top: 40px; left: 10px; z-index: 9999;width: 200px;">
          <button onclick="document.getElementById('infoBox').style.display='block'">
            ℹ️Info
          </button>
          <div id="infoBox" style="font-size:10px; color:#000; display:none; background:#fff; border:1px solid #888; padding:10px; margin-top:5px;">
            <b>Informationen</b><br>
            Die Karte das "Attraktivitätsrating" für Ostschweizer Gemeinden. Datengrundlage: WP-Daten & Urbanistica/Sotomo (2025; Studie zum Entwicklungspotenzial)<br><br>Die verschiedenen Kriterien wurden innerhalb der gewählten Gemeinden verglichen und normalisiert (zwischen 0 und 1), wobei 0 aus Investorensicht ungünstig und 1 günstig ist. Die Werte wurden dann gewichtet summiert, wobei die Summe das Gesamtrating ergab (grösser = spannender). Diese Zahl wird auf der Karte geplottet und definiert dann auch die Farbe. <br><br> Bei Fragen: ma.stutz@losinger-marazzi.ch<br><br>
            <button onclick="document.getElementById('infoBox').style.display='none'">Schliessen</button>
          </div>
        </div>
        """
        
        gewichte_button_html = f"""
        <div id="gewichteButton" style="position: fixed; bottom: 10px; left: 10px; z-index: 9999;width: 200px;">
          <button onclick="document.getElementById('sdfd').style.display='block'">
            ℹ️Gewichte
          </button>
          <div id="sdfd" style="font-size:10px; color:#000; display:none; background:#fff; border:1px solid #888; padding:10px; margin-top:5px;">
            <b>Informationen</b><br>
            Je grösser der Wert, desto attraktiver die Gemeinde für einen Investor.<br><br>
            Gewichte:<br>
            {kriterien[0]}: {g_0}<br>
            {kriterien[1]}: {g_2}<br>
            {kriterien[2]}: {g_2b}<br>
            {kriterien[3]}: {g_2c}<br>
            {kriterien[4]}: {g_3}<br>
            {kriterien[5]}: {g_4}<br>
            {kriterien[6]}: {g_5}<br>
            {kriterien[7]}: {g_6}<br>
            {kriterien[8]}: {g_7}<br>
            {kriterien[9]}: {g_8}<br>
            {kriterien[10]}: {g_9}<br>
            {kriterien[11]}: {g_10}<br>
            <br><br>
            <button onclick="document.getElementById('sdfd').style.display='none'">Schliessen</button>
          </div>
        </div>
        """
        
        
        m.get_root().html.add_child(Element(info_button_html))
        m.get_root().html.add_child(Element(gewichte_button_html))
        
        # sidepanel_html = '''
        # <div id="sidepanel" style="position:fixed; right:0; bottom:50px; width:250px; height:300px; background:#f8f8f8; border-left:2px solid #ccc; z-index:9999; padding:10px; display:none;">
        #   <b>Details & Filters</b><br>
        #   <input type="checkbox"> Layer 1<br>
        #   <input type="checkbox"> Layer 2<br>
        #   <button onclick="document.getElementById('sidepanel').style.display='none'">Close</button>
        # </div>
        # <button style="position:fixed;right:0;top:10px;z-index:9999;" onclick="document.getElementById('sidepanel').style.display='block'">☰ Menu</button>
        # '''
        # m.get_root().html.add_child(Element(sidepanel_html))
        
        lmlogo = '''
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Logo_Losinger_Marazzi.png/640px-Logo_Losinger_Marazzi.png" 
         style="position:fixed; bottom:10px; right:10px; z-index:9999; width:80px; border-radius:10px;">
        '''
        m.get_root().html.add_child(Element(lmlogo))
        
        m.add_child(folium.map.LayerControl())
        #folium.LayerControl(collapsed=False).add_to(m)
        
        # layer control verschwindet, wenn width zu breit ist! zudem muss oben der default wide mode ausgewählt werden, siehe line direkt nach den lib imports
    
        st_data = st_folium(m, height = 500, width = 1300, returned_objects=[])
    
    else:
        if not st.session_state.applied:
            st.info("Bitte oben die Kantone auswählen und Anwenden klicken.")
            st.stop()
        else:
            st.info("Bitte oben die Kantone auswählen und Anwenden klicken.")
else:
    st.stop()
