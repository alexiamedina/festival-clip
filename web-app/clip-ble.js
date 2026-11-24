// Talks to the bunny clip over Bluetooth.
// Matches PROTOCOL.md. Kept separate from the screens so a real
// App Store app later can swap just this file.

const SERVICE_UUID = "f3a1c0de-5a7e-4b1d-9c00-000000000001";
const ARTIST_UUID  = "f3a1c0de-5a7e-4b1d-9c00-000000000002";
const SCHEDULE_UUID = "f3a1c0de-5a7e-4b1d-9c00-000000000003";
const AI_UUID = "f3a1c0de-5a7e-4b1d-9c00-000000000004";
const SCENE_UUID = "f3a1c0de-5a7e-4b1d-9c00-000000000005";

export class Clip {
  constructor() {
    this.device = null;
    this.artistChar = null;
    this.onStatus = () => {};   // ("connected" | "connecting" | "disconnected", name)
    this.onReady = async () => {};  // called after every (re)connect, to resend state
  }

  static supported() {
    return !!(navigator.bluetooth && navigator.bluetooth.requestDevice);
  }

  get connected() {
    return !!(this.device && this.device.gatt.connected && this.artistChar);
  }

  // Opens the phone's "pick a device" list. Must be called from a tap.
  async connect() {
    this.device = await navigator.bluetooth.requestDevice({
      filters: [{ services: [SERVICE_UUID] }],
    });
    this.device.addEventListener("gattserverdisconnected", () => this._lost());
    await this._attach();
  }

  async _attach() {
    this.onStatus("connecting", this.device.name);
    const server = await this.device.gatt.connect();
    const service = await server.getPrimaryService(SERVICE_UUID);
    this.artistChar = await service.getCharacteristic(ARTIST_UUID);
    try { this.scheduleChar = await service.getCharacteristic(SCHEDULE_UUID); }
    catch (e) { this.scheduleChar = null; }   // clip still has the step 1 code
    try { this.aiChar = await service.getCharacteristic(AI_UUID); }
    catch (e) { this.aiChar = null; }         // clip doesn't have the AI code yet
    try { this.sceneChar = await service.getCharacteristic(SCENE_UUID); }
    catch (e) { this.sceneChar = null; }      // clip doesn't have the scene code yet
    this.onStatus("connected", this.device.name);
    await this.onReady();
  }

  // If the clip drops out (walked too far, crowd), keep trying to come back.
  async _lost() {
    this.artistChar = null;
    if (!this.device || this._manualDisconnect) {
      this._manualDisconnect = false;
      this.onStatus("disconnected");
      return;
    }
    for (let attempt = 0; attempt < 20; attempt++) {
      this.onStatus("connecting", this.device.name);
      await new Promise((r) => setTimeout(r, Math.min(1000 * 2 ** attempt, 15000)));
      try { await this._attach(); return; } catch (e) { /* try again */ }
    }
    this.onStatus("disconnected");
  }

  disconnect() {
    this._manualDisconnect = true;
    if (this.device && this.device.gatt.connected) this.device.gatt.disconnect();
    else this.onStatus("disconnected");
  }

  async _write(c, text, max = 120) {
    let bytes = new TextEncoder().encode(text);
    if (bytes.length > max) bytes = bytes.slice(0, max);
    if (c.writeValueWithResponse) await c.writeValueWithResponse(bytes);
    else await c.writeValue(bytes);
  }

  // Send an artist name. "" or "-" = no artist (bunny face).
  // This also turns the clip's auto mode off.
  async send(artist) {
    if (!this.connected) return false;
    await this._write(this.artistChar, (artist || "-").slice(0, 40));
    return true;
  }

  get canAuto() { return this.connected && !!this.scheduleChar; }

  // Hand the clip a list of sets [{artist, start: Date, end: Date}].
  // The clip then switches by itself, even while the phone sleeps.
  async sendSchedule(sets) {
    if (!this.canAuto) return false;
    const sec = (d) => Math.floor(d.getTime() / 1000);
    const c = this.scheduleChar;
    await this._write(c, "C");
    await this._write(c, "T|" + sec(new Date()));
    const upcoming = sets
      .filter((s) => s.end > new Date())
      .sort((a, b) => a.start - b.start)
      .slice(0, 80);
    for (const s of upcoming) {
      await this._write(c, `S|${sec(s.start)}|${sec(s.end)}|${s.artist.slice(0, 40)}`);
    }
    await this._write(c, "GO");
    return true;
  }

  get canAI() { return this.connected && !!this.aiChar; }

  // Send an AI look recipe line, like "bunny|FF9CC8|FFFFFF|2A0F3D|hearts|bounce|".
  // Like tapping an artist, this turns the clip's auto mode off.
  async sendLook(line) {
    if (!this.canAI) return false;
    await this._write(this.aiChar, line);
    return true;
  }

  get canScene() { return this.connected && !!this.sceneChar; }

  // Send a scene line (words + effect + background + mini-me). See PROTOCOL.md.
  async sendScene(line) {
    if (!this.canScene) return false;
    await this._write(this.sceneChar, line, 200);
    return true;
  }
}
