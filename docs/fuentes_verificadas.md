# Fuentes verificadas — cultivo de cacao e IoT Central

Consulta: 23–24 de septiembre de 2026. Escenario vigente: finca/cultivo de cacao. Autores del parcial: Daniel Villamizar y Tomas Urieles. Estas notas documentan el diseño y su trazabilidad; no acreditan que exista hardware instalado ni que una conexión haya sido probada.

## 1. Alcance de la demostración

La demostración combina simuladores, programas emisores y APIs públicas. Los sensores de esta lista son referentes para el diseño físico propuesto. Identificar por dispositivo el tipo de dato: `simulated`, `external-model`, `synthetic-replay` o `derived-operational`. La telemetría sintética no es una medición de una finca real. Los modelos meteorológicos externos no son estaciones ubicadas en la parcela.

Los umbrales de demostración se deben rotular como académicos y ajustables. Ni los límites de un datasheet ni un rango agronómico anual constituyen por sí mismos un umbral de intervención. Separar rango del sensor, resolución, exactitud/tolerancia, rango de simulación y umbral de regla.

## 2. Plataforma y protocolos

### IoT Central: disponibilidad

Microsoft mantiene documentación de creación y administración de aplicaciones. El mensaje difundido en febrero de 2024 sobre retiro en marzo de 2027 y bloqueo de nuevas aplicaciones en abril de 2024 fue corregido por Azure IoT Product Group como un mensaje erróneo. No citar esas fechas como un anuncio de retiro verificado. La elegibilidad de la suscripción del estudiante requiere validación en su sesión: documentación pública no garantiza permisos, cuota o creación exitosa.

- [Microsoft, aclaración sobre el mensaje de retiro](https://techcommunity.microsoft.com/discussions/azure-iot/azure-iot-central-retirement/4056895)
- [Crear una aplicación de IoT Central](https://learn.microsoft.com/en-us/azure/iot-central/core/howto-create-iot-central-application)
- [Descripción de IoT Central](https://learn.microsoft.com/en-us/azure/iot-central/core/overview-iot-central)

### Qué se puede automatizar con API pública

La API de IoT Central ofrece dispositivos, templates, grupos y dashboards, entre otras operaciones. `PUT /api/deviceTemplates/{id}` publica un nuevo template y genera vistas por defecto. El modelo DTDL define capacidades; las vistas son parte del template y pueden requerir personalización en la interfaz. No asumir que importar el modelo construye automáticamente todos los paneles exigidos en la rúbrica.

Los dashboards de organización admiten API; los personales no se crean por API según la documentación consultada. No apareció un grupo público de operaciones `rules` en el índice: configurar y comprobar reglas mediante la interfaz documentada, sin inventar endpoints privados.

- [Índice REST API](https://learn.microsoft.com/en-us/rest/api/iotcentral/)
- [Device Templates, API 2022-07-31](https://learn.microsoft.com/en-us/rest/api/iotcentral/dataplane/device-templates?view=rest-iotcentral-dataplane-2022-07-31)
- [Modelos, propiedades y vistas](https://github.com/MicrosoftDocs/azure-docs/blob/main/articles/iot-central/core/concepts-device-templates.md)
- [Aplicaciones y dashboards por API](https://learn.microsoft.com/en-us/azure/iot-central/core/howto-manage-iot-central-with-rest-api)
- [Reglas y acciones](https://learn.microsoft.com/en-us/azure/iot-central/core/howto-configure-rules)
- [Prueba de una regla](https://learn.microsoft.com/en-us/azure/iot-central/core/quick-configure-rules)

### MQTT, Python y HTTPS

El repositorio oficial de `azure-iot-device` indica que sus clientes Python solo soportan MQTT. DPS se usa para aprovisionar y obtener el hub asignado; no cambia el protocolo de telemetría a AMQP. Distinguir Python SDK MQTT de un cliente Paho MQTT directo: son implementaciones diferentes, no dos protocolos diferentes.

Para una ruta HTTPS real, la operación de dispositivo de IoT Hub es `POST https://{hub}.azure-devices.net/devices/{id}/messages/events?api-version=2021-04-12`; una recepción válida devuelve HTTP 204. Se usa el hub asignado por DPS y la identidad/autorización de dispositivo. La API administrativa de IoT Central no debe presentarse como endpoint de ingestión de telemetría. No registrar tokens o claves en capturas, logs ni entregables.

- [SDK Python oficial: protocolos y aprovisionamiento](https://github.com/Azure/azure-iot-sdk-python)
- [Conexión MQTT de IoT Hub](https://learn.microsoft.com/en-us/azure/iot-hub/iot-mqtt-connect-to-iot-hub)
- [Enviar evento por HTTPS](https://learn.microsoft.com/en-us/rest/api/iothub/device/device/send-device-event?view=rest-iothub-device-2021-11-30)

## 3. Diez orígenes distinguibles propuestos

Esta tabla es un diseño de integración. La evidencia final debe informar cuáles se ejecutaron realmente. Dos proyectos Wokwi cuentan como dispositivos/proyectos separados; no deben describirse como tecnologías de simulación diferentes. Dos APIs Open-Meteo aportan familias de datos y endpoints diferentes, pero pertenecen al mismo proveedor.

| # | Origen / implementación | Uso en cacao | Evidencia mínima |
|---|---|---|---|
| 1 | Simulador nativo IoT Central | Microclima de referencia | Dispositivo con `simulated=true`, template y telemetría |
| 2 | Wokwi ESP32, proyecto 1 | Temperatura y humedad del cultivo | Circuito, código, terminal serial y recepción cloud |
| 3 | Python Azure IoT Device SDK | Suelo o fermentación sintética | DPS, log MQTT SDK y recepción cloud |
| 4 | Open-Meteo Air Quality API | Contexto regional PM2.5/PM10/AQI | Respuesta JSON original, timestamp y atribución CAMS |
| 5 | Open-Meteo Weather Forecast API | Clima, lluvia, viento y radiación; alternativa académica a Atlas | URL parametrizada, respuesta original y unidades |
| 6 | Python Paho MQTT directo | Perímetro, PIR y contacto de puerta simulados | Cliente, topic MQTT, publicación y recepción |
| 7 | Replay de CSV sintético documentado | Evolución de fermentación o riego | CSV, procedencia sintética, timestamp original y de reemisión |
| 8 | HTTPS REST de IoT Hub | Tanque, caudal o estado de bomba simulado | POST saneado, HTTP 204 y valor cloud |
| 9 | Wokwi ESP32, proyecto 2 | Riego/depósito, pulsadores o potenciómetros | Proyecto independiente, circuito y recepción cloud |
| 10 | Node.js MQTT.js y agregador | Estado operativo a partir de eventos/logs reales de la demo | Código, origen de los conteos y telemetría derivada |

No contar cambiar un `deviceId` como nuevo origen de datos. Mantener conectividad y evidencia por ruta. `connectedCount`, `disconnectedCount` y `unassociatedCount` deben derivarse de un criterio documentado (estado de plataforma o heartbeat) y no de números aleatorios. Un productor detenido no demuestra necesariamente desconexión inmediata en la plataforma.

[Wokwi: ESP32 y acceso a Internet](https://docs.wokwi.com/guides/esp32-wifi). El gateway público permite tráfico saliente y tiene monitoreo/limitaciones; el acceso a la red local requiere gateway privado. [DHT22 en Wokwi](https://docs.wokwi.com/parts/wokwi-dht22): sus valores son controles del simulador; recomienda DHT sensor library for ESPx para ESP32.

## 4. Sensores de referencia y unidades

### Suelo, microclima y poscosecha

| Variable | Referente y rango | Resolución / exactitud especificada | Interpretación |
|---|---|---|---|
| Humedad volumétrica de suelo | METER TEROS 12: 0–0.70 m³/m³ con calibración mineral; 0–1.0 en sustrato | 0.001 m³/m³; ±0.03 m³/m³ típica con calibración genérica mineral y EC de solución <8 dS/m | Para `% VWC`, multiplicar por 100. No confundir con humedad relativa del aire ni porcentaje ADC |
| Temperatura de suelo | TEROS 12: −40 a 60 °C | 0.1 °C; ±1 °C entre −40 y 0; ±0.5 °C entre 0 y 60 | Medir zona radicular con instalación y contacto adecuados |
| Conductividad eléctrica aparente bulk | TEROS 12: 0–20,000 µS/cm = 0–20 dS/m | 1 µS/cm; ±(5% de lectura +10 µS/cm) hasta 10,000; ±8% de 10,000 a 20,000 | No es directamente EC del extracto de pasta saturada; no inferir nutrientes individuales |
| Aire: temperatura / humedad | Aosong AM2302/DHT22: −40 a 80 °C; 0–99.9 %RH extendido | Resolución 0.1; típica ±0.5 °C y ±2 %RH bajo condiciones del manual | No dar esas precisiones como uniformes en todo el rango; gráficas muestran mayor error en extremos; lectura mínima cada 2 s |
| Masa en fermentación | Analog Devices DS18B20: −55 a 125 °C | ±0.5 °C entre −10 y 85; ±1 entre −30 y 100; ±2 en todo el rango; 9–12 bits | Sonda encapsulada y contacto con la masa se deben especificar aparte; el chip solo no acredita aptitud alimentaria |
| Humectación foliar | METER PHYTOS 31: salida aproximada 300–1250 mV según excitación | Estado mojado/seco: exactitud porcentual N/A; la fuente documenta salida y umbral dependiente del sistema | Reportar `leafWet` boolean o duración acumulada. Un índice sintético 0–100 no es %RH ni % de agua foliar medido |

Fuentes primarias:

- [TEROS 12 — especificaciones del fabricante](https://metergroup.com/products/teros-12/), [manual TEROS 11/12](https://publications.metergroup.com/Manuals/20587_TEROS11-12_Manual_Web.pdf).
- [AM2302 — manual Aosong V1.0, tabla y gráficas de página 2](https://www.aosong.com/uploadfiles/2025/04/20250417105409216.pdf). Alcance normal de humedad 0–80 %RH; humedad alta prolongada puede producir deriva. Las especificaciones de precisión dependen de 25 °C, 5 V y ausencia de condensación.
- [DS18B20 — datasheet Rev.6](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf).
- [PHYTOS 31 — manual](https://library.metergroup.com/Manuals/20434_PHYTOS31_Manual_Web.pdf), [producto](https://metergroup.com/products/phytos-31/).

### Meteorología, luz y riego

| Variable | Referente / rango | Exactitud, resolución o limitación |
|---|---|---|
| Viento | Vaisala WXT530: observación 0–60 m/s | ±3% a 10 m/s; resolución 0.1 m/s |
| Dirección de viento | Vaisala WXT530: 0–360° | ±3° a 10 m/s; resolución 1° |
| Intensidad de lluvia | Vaisala WXT530: 0–200 mm/h | Resolución 0.1 mm/h; no confundir con acumulación |
| Acumulación de lluvia | Vaisala WXT530 | Resolución 0.01 mm; exactitud de acumulación diaria mejor que 5%, dependiente del clima, excluye posibles errores por viento |
| Radiación solar | Apogee SP-110-SS: salida 0–400 mV; factor 5 W/m² por mV | Intervalo equivalente de salida 0–2000 W/m²; incertidumbre de calibración <3% a 1000 W/m²; no equivale a exactitud total bajo todo cielo |
| Iluminancia | ROHM BH1750FVI: 1–65,535 lx nominales | 1 lx en modo alta resolución; variación ±20% según ficha. No convertir lux a W/m² con un factor universal |
| Distancia a superficie del tanque | MaxBotix MB7389: 300–5000 mm | Resolución 1 mm. No atribuir precisión ±1 mm: resolución y exactitud son diferentes |
| Caudal de riego | DFRobot SEN0217: 1–30 L/min | ±5% entre 2–30 L/min; 450 pulsos/L. Caudales muy bajos quedan fuera del rango especificado |

Fuentes primarias:

- [Vaisala WXT530 datasheet B211500EN-K](https://docs.vaisala.com/api/khub/documents/8mSgE_e9EAq~QTD3lSKELQ/content).
- [Apogee SP-110-SS, ficha de producto](https://www.apogeeinstruments.com/sp-110-ss-self-powered-pyranometer/), [manual](https://www.apogeeinstruments.com/content/SP-110-manual.pdf). Se prioriza la ficha actual; otras páginas antiguas de FAQ usan 350 mV/1750 W/m².
- [ROHM BH1750FVI, ficha original Rev.D alojada por Mouser](https://www.mouser.com/datasheet/2/348/bh1750fvi-e-186247.pdf). El enlace de fabricante no respondió en la consulta; el documento conserva autoría ROHM y está enlazado desde el [fabricante de la placa Adafruit](https://learn.adafruit.com/adafruit-bh1750-ambient-light-sensor/downloads).
- [MaxBotix MB7389](https://maxbotix.com/products/mb7389?country=GB&currency=GBP&variant=48771213623583).
- [DFRobot SEN0217](https://wiki.dfrobot.com/sen0217).

El nivel porcentual de tanque es una variable calculada con geometría: `100 × (distancia_vacío − distancia_actual)/(distancia_vacío − distancia_lleno)`, limitada a 0–100 y con diagnóstico fuera de rango. El volumen requiere geometría; no es necesariamente proporcional a altura en depósitos horizontales. El caudal, nivel y orden de bomba permiten una regla demostrativa: bomba encendida + caudal bajo sostenido = revisar obstrucción, falta de agua o fallo.

### Calidad ambiental y seguridad perimetral

| Variable | Referente | Rango / precisión y observación |
|---|---|---|
| PM2.5 / PM10 | Sensirion SPS30 | 0–1000 µg/m³. PM1/PM2.5: ±(5 µg/m³ +5% lectura) hasta 100, ±10% sobre 100. PM4/PM10: ±25 µg/m³ hasta 100 y ±25% sobre 100; el fabricante lo llama precisión/variación entre unidades |
| CO₂ opcional | Sensirion SCD41, datasheet1.7 abril2025 | Rango especificado 400–5000 ppm: ±(50ppm+2.5%) a400–1000; ±(50ppm+3%) a1001–2000; ±(40ppm+5%) a2001–5000. Salida 0–40000ppm no significa precisión garantizada en todo ese intervalo |
| Movimiento | Panasonic PaPIRs EKMB1101112 | Digital, alcance nominal 5 m. `motion` boolean sin unidad; precisión porcentual N/A. No identifica personas ni garantiza ocupación |
| Apertura | Littelfuse 59025, variante1/S normalmente abierta | Contacto boolean, precisión N/A. Distancias de tabla: activación5.1mm/desactivación17mm con configuración/actuador especificados; no generalizar a todo reed |
| Humo/gas relativo | Winsen MQ-2 como referente | La ficha declara gas inflamable300–10000ppm, pero una lectura ADC sin calibración y gas definido NO acredita ppm. En demo usar `smoke` como índice relativo o boolean identificado |

Fuentes:

- [SPS30, datasheet2.0](https://sensirion.com/file/datasheet_sps30).
- [SCD4x, datasheet1.7 abril2025](https://sensirion.com/media/documents/48C4B7FB/67FE0194/CD_DS_SCD4x_Datasheet_D1.pdf).
- [Panasonic EKMB1101112](https://industrial.panasonic.com/sa/products/pt/papirs/models/EKMB1101112).
- [Littelfuse59025 datasheet](https://www.littelfuse.com/assetdocs/littelfuse_reed_sensors_59025_datasheet.pdf?assetguid=6a907dc7-81d0-49b2-9f67-d3cea7dfe09b).
- [Winsen MQ-2](https://www.winsen-sensor.com/product/mq-2.html).

Para `flame`, `doorOpen`, `motion`, `pumpOn` y `alarmAck`, usar boolean y sin unidad. Si se emulan con interruptor/pulsador, explicitarlo; un interruptor en Wokwi no es un detector físico de llama ni un contacto instalado.

## 5. Contexto agronómico del cacao

ICCO describe condiciones climáticas generales favorables con promedio anual de máximas de30–32°C y de mínimas de18–21°C; lluvia preferida1500–2000mm/año bien distribuida y no más de tres meses con menos de100mm/mes. Estas son referencias de clima y cultivo, no alarmas instantáneas de temperatura ni consignas de riego. Fuente: [ICCO Growing Cocoa](https://www.icco.org/growing-cocoa/).

Durante fermentación, ICCO describe40–45°C en las primeras48h. AGROSAVIA explica que el perfil depende de variedad, madurez y composición y menciona aproximadamente50°C hacia96h. La curva de un replay debe declararse ejemplo sintético, asociarse a edad del lote y no presentarse como receta universal. Fuentes: [ICCO Harvesting & Post-harvest](https://www.icco.org/harvesting-post-harvest-new/), [AGROSAVIA, estrategias de beneficio del cacao](https://www.agrosavia.co/media/11517/ver_documento_36651.pdf).

Propuesta académica para demostrar reglas (decisiones de diseño, no umbrales agronómicos certificados):

- Suelo seco: `% VWC <20` sostenido, con histéresis de recuperación por encima de25; ajustar al suelo, curva de retención y profundidad antes de usar en campo.
- Tanque bajo: nivel<20%; fallo de riego: bomba encendida con caudal<2L/min durante ventana definida. Adaptar a geometría, bomba y emisor reales.
- Fermentación: alarma de revisión si temperatura>55°C; condición de baja temperatura debe depender de horas desde inicio, no de un límite único para todas las fases.
- Humectación: alertar por duración continua larga elegida para la demo. No afirmar diagnóstico de moniliasis/Phytophthora a partir de un boolean.
- Perímetro: movimiento y puerta abierta durante un intervalo configurado; no inferir identidad ni delito.

## 6. APIs, unidades y procedencia

[Open-Meteo Weather Forecast API](https://open-meteo.com/en/docs) proporciona datos modelados. Conservar el campo de unidades y el timestamp original. `wind_speed_10m` puede devolverse en km/h o m/s según parámetro. `shortwave_radiation` se expresa en W/m² y los datos horarios representan promedio de la hora precedente. La precipitación horaria es acumulación en mm durante la hora anterior; no renombrarla automáticamente como intensidad instantánea mm/h. Si se deriva una tasa, conservar duración y fórmula.

[Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) ofrece PM2.5/PM10 en µg/m³. Para Colombia, el origen general es CAMS global (~45km), no una estación al interior de la finca. Seleccionar explícitamente `us_aqi` o `european_aqi`: no intercambiar sus escalas. AQI es un índice sin unidad física; no llamarlo ppm ni % y no asumir que siempre está limitado a500. La página exige atribución a Open-Meteo y a CAMS. Mantener `sourceTimestamp` e `ingestionTimestamp` separados; reutilizar una respuesta cada30s no crea una observación meteorológica nueva cada30s.

Atlas no se ejecutó por el solo hecho de consumir Open-Meteo. El informe debe decir “Open-Meteo como fuente meteorológica equivalente para el ejercicio” y documentar por qué aporta las variables requeridas; la equivalencia académica depende de la rúbrica/profesor.

## 7. Telecomunicaciones rurales propuestas

Arquitectura física conceptual: sensores → nodo/gateway local → router4G/LTE → Internet → DPS/IoT Hub/IoT Central; Starlink como alternativa donde haya cobertura satelital y cielo despejado. [Teltonika RUT241](https://www.teltonika-networks.com/products/routers/rut241) documenta LTE Cat4, Wi-Fi, Ethernet y WAN failover. [Especificaciones Starlink](https://www.starlink.com/legal/documents/DOC-1431-92252-65) advierten variación de rendimiento y ausencia de garantía de servicio ininterrumpido.

No atribuir estas rutas a la demo si los programas usaron la conexión actual del computador. Para el diseño rural se deben contemplar cola local con timestamp, reintentos, límite de consumo, respaldo de energía y recuperación de enlace. No se midieron cobertura, latencia, RSRP ni disponibilidad en una finca real durante la investigación.

## 8. Evidencias y limitaciones que deben quedar explícitas

1. Solo declarar integrado un origen tras observar recepción en IoT Central, timestamp y valor coherente.
2. Guardar screenshot del template, dispositivo, fuente y panel para poder relacionarlos.
3. Un HTTP204 confirma aceptación del mensaje por el servicio; completar con visualización/consulta cloud para confirmar esquema.
4. Mostrar disparo real de una regla con valores simulados intencionales y etiquetar el incidente como prueba.
5. No inventar capturas, correos recibidos, mediciones de campo, latencias ni precisión experimental.
6. Las referencias de sensores físicos no implican que fueron comprados, calibrados o desplegados.
