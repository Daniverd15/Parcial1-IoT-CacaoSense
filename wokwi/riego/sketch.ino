/*
 * CacaoSense | Nodo 09 - Reservorio / riego (Wokwi ESP32 #2, segunda instancia)   firmware v1.1.0
 * ESP32 virtual -> Azure IoT Central via DPS + MQTT/TLS 8883 (PubSubClient, SAS con mbedTLS).
 *
 *   HC-SR04 TRIG 5 / ECHO 18 -> waterLevel (%)   analogo a MaxBotix MB7389 (tanque: 200 cm vacio / 20 cm lleno)
 *   Potenciometro GPIO35     -> flowRate (L/min, 0..30) analogo a DFRobot SEN0217 (solo con bomba ON)
 *   LED azul GPIO13          -> pumpOn  <- comando setPump(true/false); enclavamiento si nivel < 10 %
 *   Envio cada 30 s. Credenciales: rellenar SOLO en la copia que se pega en Wokwi (no subir la clave).
 */
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "mbedtls/md.h"
#include "mbedtls/base64.h"

#define ID_SCOPE   "PEGAR_ID_SCOPE"
#define DEVICE_ID  "cacao-09-riego-wokwi"
#define DEVICE_KEY "PEGAR_PRIMARY_KEY"
#define FW_VERSION "riego.ino v1.1.0"
#define SEND_INTERVAL_MS 30000

#define TRIG_PIN 5
#define ECHO_PIN 18
#define FLOW_PIN 35
#define LED_PIN 13
#define EMPTY_CM 200.0f
#define FULL_CM 20.0f

const char *DPS_HOST = "global.azure-devices-provisioning.net";
WiFiClientSecure net;
PubSubClient mqtt(net);
uint8_t decodedKey[64];
size_t decodedKeyLen = 0;
volatile bool msgArrived = false;
String inTopic, inPayload, assignedHub = "";
unsigned long lastSend = 0, seq = 0;
bool pumpOn = false;

float waterLevel() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10); digitalWrite(TRIG_PIN, LOW);
  float cm = pulseIn(ECHO_PIN, HIGH, 30000) / 58.0f;
  float pct = 100.0f * (EMPTY_CM - cm) / (EMPTY_CM - FULL_CM);
  return roundf(constrain(pct, 0.0f, 100.0f) * 10) / 10.0f;
}

String urlEncode(const String &s) {
  String o; const char *hex = "0123456789ABCDEF";
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') o += c;
    else { o += '%'; o += hex[(c >> 4) & 0xF]; o += hex[c & 0xF]; }
  }
  return o;
}

String sasToken(const String &uri) {
  unsigned long se = (unsigned long)time(nullptr) + 24UL * 3600UL;
  String enc = urlEncode(uri), toSign = enc + "\n" + String(se);
  uint8_t mac[32]; mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx); mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
  mbedtls_md_hmac_starts(&ctx, decodedKey, decodedKeyLen);
  mbedtls_md_hmac_update(&ctx, (const unsigned char *)toSign.c_str(), toSign.length());
  mbedtls_md_hmac_finish(&ctx, mac); mbedtls_md_free(&ctx);
  unsigned char b64[64]; size_t olen = 0;
  mbedtls_base64_encode(b64, sizeof(b64), &olen, mac, 32); b64[olen] = 0;
  return "SharedAccessSignature sr=" + enc + "&sig=" + urlEncode(String((char *)b64)) + "&se=" + String(se);
}

void reply(const String &topic, int status, const String &body) {
  String rid = topic.substring(topic.indexOf("$rid=") + 5);
  mqtt.publish(("$iothub/methods/res/" + String(status) + "/?$rid=" + rid).c_str(), body.c_str());
}

void onMessage(char *topic, byte *payload, unsigned int len) {
  inTopic = String(topic); inPayload = "";
  for (unsigned int i = 0; i < len; i++) inPayload += (char)payload[i];
  msgArrived = true;
  if (inTopic.startsWith("$iothub/methods/POST/setPump")) {
    bool want = inPayload.indexOf("true") >= 0;
    if (want && waterLevel() < 10.0f) {
      Serial.println("[INTERLOCK] setPump(true) rechazado: reservorio < 10 %");
      reply(inTopic, 409, "\"Rechazado: nivel del reservorio < 10 %\"");
      return;
    }
    pumpOn = want;
    digitalWrite(LED_PIN, pumpOn ? HIGH : LOW);
    Serial.printf("[CMD] setPump(%s) -> bomba %s\n", inPayload.c_str(), pumpOn ? "ON" : "OFF");
    reply(inTopic, 200, String("\"Bomba de riego ") + (pumpOn ? "ENCENDIDA" : "APAGADA") + "\"");
  } else if (inTopic.startsWith("$iothub/methods/POST/")) {
    reply(inTopic, 404, "\"comando no soportado\"");
  }
}

bool waitMsg(unsigned long ms) {
  unsigned long t = millis(); msgArrived = false;
  while (!msgArrived && millis() - t < ms) { mqtt.loop(); delay(20); }
  return msgArrived;
}

String runDps() {
  Serial.println("[DPS] Registro en global.azure-devices-provisioning.net:8883");
  net.setInsecure();                                   // Wokwi-GUEST: laboratorio
  mqtt.setServer(DPS_HOST, 8883); mqtt.setBufferSize(2048); mqtt.setCallback(onMessage);
  String user = String(ID_SCOPE) + "/registrations/" + DEVICE_ID + "/api-version=2019-03-31";
  String pass = sasToken(String(ID_SCOPE) + "/registrations/" + DEVICE_ID) + "&skn=registration";
  while (!mqtt.connect(DEVICE_ID, user.c_str(), pass.c_str())) { Serial.printf("[DPS] rc=%d\n", mqtt.state()); delay(3000); }
  mqtt.subscribe("$dps/registrations/res/#");
  mqtt.publish("$dps/registrations/PUT/iotdps-register/?$rid=1", (String("{\"registrationId\":\"") + DEVICE_ID + "\"}").c_str());
  String op = "";
  if (waitMsg(10000)) { StaticJsonDocument<1024> d; if (!deserializeJson(d, inPayload)) op = (const char *)(d["operationId"] | ""); }
  for (int i = 0; i < 10 && assignedHub == ""; i++) {
    delay(2000);
    mqtt.publish(("$dps/registrations/GET/iotdps-get-operationstatus/?$rid=2&operationId=" + op).c_str(), "{}");
    if (waitMsg(10000)) {
      StaticJsonDocument<1024> d;
      if (!deserializeJson(d, inPayload) && String((const char *)(d["status"] | "")) == "assigned")
        assignedHub = (const char *)d["registrationState"]["assignedHub"];
    }
  }
  mqtt.disconnect();
  Serial.printf("[DPS] assignedHub = %s\n", assignedHub.c_str());
  return assignedHub;
}

void connectHub() {
  mqtt.setServer(assignedHub.c_str(), 8883);
  String user = assignedHub + "/" + DEVICE_ID + "/?api-version=2021-04-12";
  while (!mqtt.connected()) {
    Serial.println("[HUB] Connecting...");
    if (mqtt.connect(DEVICE_ID, user.c_str(), sasToken(assignedHub + "/devices/" + DEVICE_ID).c_str())) {
      Serial.println("[HUB] CONNECTED (IoT Central: Connected)");
      mqtt.subscribe("$iothub/methods/POST/#");
      mqtt.publish("$iothub/twin/PATCH/properties/reported/?$rid=10",
                   "{\"firmwareVersion\":\"" FW_VERSION "\",\"zone\":\"Reservorio / riego\",\"originId\":\"Wokwi ESP32 #2\"}");
    } else { Serial.printf("[HUB] rc=%d, reintento\n", mqtt.state()); delay(3000); }
  }
}

void publishTelemetry() {
  float level = waterLevel();
  if (pumpOn && level < 10.0f) { pumpOn = false; digitalWrite(LED_PIN, LOW); Serial.println("[INTERLOCK] bomba apagada: nivel < 10 %"); }
  StaticJsonDocument<192> doc;
  doc["waterLevel"] = level;
  doc["flowRate"] = pumpOn ? roundf(analogRead(FLOW_PIN) * 300.0f / 4095.0f) / 10.0f : 0.0f;
  doc["pumpOn"] = pumpOn;
  char buf[192]; size_t n = serializeJson(doc, buf);
  bool ok = mqtt.publish((String("devices/") + DEVICE_ID + "/messages/events/").c_str(), (const uint8_t *)buf, n, false);
  Serial.printf("[TX #%lu] %s %s\n", ++seq, ok ? "OK" : "FALLO", buf);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT); digitalWrite(LED_PIN, LOW);
  pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);
  analogReadResolution(12);
  Serial.println("CacaoSense | " FW_VERSION " | " DEVICE_ID);
  mbedtls_base64_decode(decodedKey, sizeof(decodedKey), &decodedKeyLen, (const unsigned char *)DEVICE_KEY, strlen(DEVICE_KEY));
  WiFi.begin("Wokwi-GUEST", "");
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.printf("\n[WiFi] OK IP=%s\n", WiFi.localIP().toString().c_str());
  configTime(0, 0, "pool.ntp.org");
  while (time(nullptr) < 1700000000) delay(300);
  Serial.printf("[NTP] epoch=%ld\n", (long)time(nullptr));
  if (runDps() != "") connectHub();
}

void loop() {
  if (!mqtt.connected() && assignedHub != "") { Serial.println("[HUB] DISCONNECTED -> reconexion"); connectHub(); }
  mqtt.loop();
  if (millis() - lastSend > SEND_INTERVAL_MS) { lastSend = millis(); publishTelemetry(); }
}
