/**
 * Baicells SMS Card
 * A phone-style chat view for the Baicells SMS integration's inbox sensor.
 *
 * Usage in a Lovelace dashboard (YAML mode):
 *
 *   type: custom:baicells-sms-card
 *   entity: sensor.baicells_sms_inbox
 *   title: SMS Messages
 *   max_height: 420px
 *
 * This file is served and auto-loaded by the Baicells SMS integration; no
 * manual resource registration is required.
 */
class BaicellsSmsCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Please define an entity (the Baicells SMS inbox sensor).");
    }
    this._config = config;
    this._rendered = false;
    this._lastSignature = null;
  }

  set hass(hass) {
    this._hass = hass;
    const entityId = this._config.entity;
    const stateObj = hass.states[entityId];

    if (!this._rendered) {
      this._renderBase();
      this._rendered = true;
    }

    if (!stateObj) {
      this._body.innerHTML = `<div class="bsc-empty">Entity "${entityId}" was not found.</div>`;
      this._lastSignature = null;
      return;
    }

    const rawMessages = Array.isArray(stateObj.attributes.messages)
      ? stateObj.attributes.messages
      : [];

    // The integration stores messages newest-first; reverse for a natural
    // top-to-bottom chat reading order (oldest at top, newest at bottom).
    const messages = rawMessages.slice().reverse();

    const signature = messages
      .map((m) => m.signature || `${m.sender}|${m.timestamp}|${m.text}`)
      .join("\u0001");

    if (signature === this._lastSignature) {
      return;
    }
    this._lastSignature = signature;

    this._renderMessages(messages);
  }

  _renderBase() {
    const title = this._config.title !== undefined ? this._config.title : "SMS Messages";
    const maxHeight = this._config.max_height || "420px";

    this.innerHTML = `
      <ha-card>
        ${title ? `<div class="bsc-header">${this._escape(title)}</div>` : ""}
        <div class="bsc-body" style="max-height:${this._escape(maxHeight)}"></div>
      </ha-card>
      <style>
        ha-card {
          overflow: hidden;
        }
        .bsc-header {
          padding: 16px 16px 4px 16px;
          font-size: 1.2em;
          font-weight: 500;
          color: var(--ha-card-header-color, var(--primary-text-color));
        }
        .bsc-body {
          overflow-y: auto;
          padding: 12px 12px 16px 12px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          background: var(--ha-card-background, var(--card-background-color));
        }
        .bsc-empty {
          padding: 24px 16px;
          color: var(--secondary-text-color);
          text-align: center;
        }
        .bsc-msg {
          max-width: 82%;
          align-self: flex-start;
          display: flex;
          flex-direction: column;
        }
        .bsc-sender {
          font-size: 0.72em;
          font-weight: 600;
          color: var(--secondary-text-color);
          margin: 0 0 3px 6px;
        }
        .bsc-bubble {
          background: var(--divider-color, #e4e4e7);
          color: var(--primary-text-color);
          padding: 8px 12px;
          border-radius: 16px 16px 16px 4px;
          white-space: pre-wrap;
          word-break: break-word;
          font-size: 0.95em;
          line-height: 1.35;
          box-shadow: 0 1px 1px rgba(0, 0, 0, 0.08);
        }
        .bsc-time {
          font-size: 0.68em;
          color: var(--secondary-text-color);
          margin: 3px 0 0 6px;
        }
      </style>
    `;
    this._body = this.querySelector(".bsc-body");
  }

  _renderMessages(messages) {
    if (!messages.length) {
      this._body.innerHTML = '<div class="bsc-empty">No saved SMS messages yet.</div>';
      return;
    }

    this._body.innerHTML = messages
      .map(
        (m) => `
          <div class="bsc-msg">
            <div class="bsc-sender">${this._escape(m.sender)}</div>
            <div class="bsc-bubble">${this._escape(m.text)}</div>
            <div class="bsc-time">${this._escape(m.timestamp)}</div>
          </div>
        `
      )
      .join("");

    // Auto-scroll to the most recent message, like a phone messaging app.
    this._body.scrollTop = this._body.scrollHeight;
  }

  _escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig(hass) {
    const entities = hass && hass.states ? Object.keys(hass.states) : [];
    const match = entities.find((id) => id.startsWith("sensor.baicells_sms"));
    return { entity: match || "", title: "SMS Messages" };
  }
}

customElements.define("baicells-sms-card", BaicellsSmsCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "baicells-sms-card",
  name: "Baicells SMS Card",
  description: "Displays Baicells SMS inbox messages in a phone-style chat view.",
});
