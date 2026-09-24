#!/usr/bin/env node
// CacaoSense | nodo 10 Perimetro / bodega - Node.js + MQTT.js (cliente MQTT explicito en JavaScript).
// DPS por MQTT -> IoT Hub por MQTT/TLS 8883 con SAS generado con crypto (HMAC-SHA256).
// Comando setAlertLed (sirena/LED de perimetro). Credenciales desde ../.env (nunca se imprimen).
//   node bodega.js [--count N] [--interval S]
'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const mqtt = require('mqtt');

const VERSION = 'bodega.js v1.0.0';
const DEV = 'cacao-10-bodega-mqttjs';
const env = Object.fromEntries(fs.readFileSync(path.join(__dirname, '..', '.env'), 'utf8')
  .split(/\r?\n/).filter(l => l && !l.startsWith('#') && l.includes('='))
  .map(l => [l.slice(0, l.indexOf('=')).trim(), l.slice(l.indexOf('=') + 1).trim()]));
const SCOPE = env.IOTC_ID_SCOPE;
const KEY = env.CACAO_10_BODEGA_MQTTJS_DEVICE_KEY;
const arg = n => { const i = process.argv.indexOf(n); return i > 0 ? Number(process.argv[i + 1]) : 0; };
const COUNT = arg('--count');
let interval = (arg('--interval') || 20) * 1000;

const log = m => console.log(`${new Date().toISOString().replace('T', ' ').slice(0, 19)} [${DEV}] ${m}`);

function sas(resource, key, policy, ttl = 3600) {
  const uri = encodeURIComponent(resource);
  const se = Math.floor(Date.now() / 1000) + ttl;
  const sig = crypto.createHmac('sha256', Buffer.from(key, 'base64')).update(`${uri}\n${se}`).digest('base64');
  return `SharedAccessSignature sr=${uri}&sig=${encodeURIComponent(sig)}&se=${se}` + (policy ? `&skn=${policy}` : '');
}

function dpsRegister() {
  return new Promise((resolve, reject) => {
    const c = mqtt.connect('mqtts://global.azure-devices-provisioning.net:8883', {
      clientId: DEV, protocolVersion: 4, reconnectPeriod: 0,
      username: `${SCOPE}/registrations/${DEV}/api-version=2019-03-31`,
      password: sas(`${SCOPE}/registrations/${DEV}`, KEY, 'registration'),
    });
    c.on('connect', () => {
      log('[DPS] CONNACK; PUBLISH $dps/registrations/PUT/iotdps-register/?$rid=1');
      c.subscribe('$dps/registrations/res/#', { qos: 1 });
      c.publish('$dps/registrations/PUT/iotdps-register/?$rid=1', JSON.stringify({ registrationId: DEV }), { qos: 1 });
    });
    c.on('message', (topic, buf) => {
      const body = JSON.parse(buf.toString() || '{}');
      if (topic.includes('/res/202')) {
        setTimeout(() => c.publish(`$dps/registrations/GET/iotdps-get-operationstatus/?$rid=2&operationId=${body.operationId}`, '', { qos: 1 }), 2000);
      } else if (topic.includes('/res/200')) {
        c.end(); resolve(body.registrationState.assignedHub);
      } else { c.end(); reject(new Error('DPS ' + topic)); }
    });
    c.on('error', reject);
  });
}

// Modelo de bodega: puerta y movimiento en horario de trabajo (07-17 h local).
let seq = 0;
function sample() {
  const now = new Date();
  const h = ((now.getUTCHours() - 5 + 24) % 24) + now.getUTCMinutes() / 60;
  const day = h >= 6 && h <= 18 ? Math.sin(Math.PI * (h - 6) / 12) : 0;
  const work = h >= 7 && h <= 17;
  const doorOpen = work && (seq % 9 === 0 || seq % 9 === 1);
  const motion = doorOpen || (work && Math.random() < 0.25) || (!work && Math.random() < 0.02);
  const out = { doorOpen, motion, temperature: Math.round((25 + 4 * day + (Math.random() - 0.5) * 0.4) * 10) / 10 };
  // Puesto de mando: estado agregado de la flota calculado por fleet_monitor.py (criterio heartbeat).
  try {
    const fleet = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'fleet.json'), 'utf8'));
    if (Date.now() - Date.parse(fleet.at) < 5 * 60 * 1000) {
      out.fleetConnected = fleet.counts.Connected;
      out.fleetDisconnected = fleet.counts.Disconnected;
      out.fleetUnassociated = fleet.counts.Unassociated;
    }
  } catch (e) { /* sin snapshot reciente: no se reporta estado de flota */ }
  return out;
}

(async () => {
  log(`${VERSION} | origen: Node.js MQTT.js | intervalo ${interval / 1000}s`);
  const hub = await dpsRegister();
  log(`[DPS] assigned -> ${hub}`);
  const c = mqtt.connect(`mqtts://${hub}:8883`, {
    clientId: DEV, protocolVersion: 4, reconnectPeriod: 2000, keepalive: 120,
    username: `${hub}/${DEV}/?api-version=2021-04-12`,
    password: sas(`${hub}/devices/${DEV}`, KEY, null, 24 * 3600),
  });
  let timer = null;
  c.on('connect', () => {
    log(`[HUB] CONNECTED ${hub}:8883`);
    c.subscribe('$iothub/methods/POST/#', { qos: 0 });
    if (timer) return;
    const tick = () => {
      const data = sample(); seq++;
      const body = JSON.stringify(data);
      c.publish(`devices/${DEV}/messages/events/`, body, { qos: 1 }, err =>
        log(err ? `[TX #${seq}] error ${err.message}` : `[TX #${seq}] PUBACK qos=1 bytes=${body.length} ${body}`));
      if (COUNT && seq >= COUNT) { setTimeout(() => { log('[FIN] DISCONNECT'); c.end(); process.exit(0); }, 2000); return; }
      timer = setTimeout(tick, interval);
    };
    tick();
  });
  c.on('close', () => log('[HUB] DISCONNECTED; MQTT.js reintenta cada 2 s'));
  c.on('message', (topic, buf) => {
    const name = topic.split('/POST/')[1].split('/')[0];
    const rid = topic.split('$rid=')[1];
    const on = JSON.parse(buf.toString() || 'null') === true;
    const result = name === 'setAlertLed' ? `Sirena/LED de bodega ${on ? 'ON' : 'OFF'}` : `comando ${name} no soportado`;
    log(`[CMD] ${name}(${buf}) -> ${result}`);
    c.publish(`$iothub/methods/res/200/?$rid=${rid}`, JSON.stringify(result), { qos: 0 });
  });
  const stop = () => { log('[FIN] DISCONNECT controlado'); c.end(true); process.exit(0); };
  process.on('SIGINT', stop); process.on('SIGTERM', stop);
})().catch(e => { log('ERROR ' + e.message); process.exit(1); });
