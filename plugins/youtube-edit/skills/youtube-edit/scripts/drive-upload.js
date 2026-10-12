#!/usr/bin/env node
// drive-upload.js <localPath> <mimeType> [name]: private upload into the config's delivery.drive_api.folder_id with the
// USER'S OWN Google OAuth app, whose keys are read by name from the user's Keychain. Prints {id,name,size,webViewLink}.
// googleapis is resolved from delivery.drive_api.googleapis_dir, else the working folder's node_modules.
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const cfg = JSON.parse(execFileSync('python3', [path.join(__dirname, 'ytconfig.py'), 'get', 'delivery'], { encoding: 'utf8' }));
const workdir = execFileSync('python3', [path.join(__dirname, 'ytconfig.py'), 'get', 'workdir'], { encoding: 'utf8' }).trim();
const api = cfg.drive_api;
const dirs = [api.googleapis_dir && api.googleapis_dir.replace(/^~/, process.env.HOME), path.join(workdir, 'node_modules')].filter(Boolean);
let google;
for (const d of dirs) { try { ({ google } = require(path.join(d, 'googleapis'))); break; } catch (e) {} }
if (!google) { console.error(`googleapis not found in ${dirs.join(' or ')} (cd ${workdir} && npm i googleapis)`); process.exit(1); }
const k = a => execFileSync('security', ['find-generic-password', '-s', api.keychain_service, '-a', a, '-w'], { encoding: 'utf8' }).trim();
(async () => {
  const [p, mime, name] = process.argv.slice(2);
  if (!p || !mime) { console.error('usage: drive-upload.js <file> <mimeType> [name]'); process.exit(1); }
  if (!api.folder_id) { console.error('config delivery.drive_api.folder_id is empty'); process.exit(1); }
  const o = new google.auth.OAuth2(k(api.client_id_key), k(api.client_secret_key));
  o.setCredentials({ refresh_token: k(api.refresh_token_key) });
  const d = google.drive({ version: 'v3', auth: o }); const size = fs.statSync(p).size;
  const r = await d.files.create({ requestBody: { name: name || path.basename(p), parents: [api.folder_id] },
    media: { mimeType: mime, body: fs.createReadStream(p) }, fields: 'id,name,size,webViewLink' },
    { onUploadProgress: e => { if (size > 5e7) process.stderr.write(`\r${(100 * e.bytesRead / size).toFixed(0)}%`); } });
  if (Number(r.data.size) !== size) { console.error(`SIZE MISMATCH: local ${size}, drive ${r.data.size} (id ${r.data.id}): trash it and retry`); process.exit(2); }
  console.log(JSON.stringify(r.data));
})().catch(e => { console.error(e.message); process.exit(1); });
