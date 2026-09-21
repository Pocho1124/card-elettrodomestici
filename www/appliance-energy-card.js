// Appliance Energy Card v4 — custom Lovelace card
//
// Config MINIMA (con l'integrazione "Card Elettrodomestici" installata,
// state_entity espone da solo immagini, potenza, cicli e costo come attributi):
// type: custom:appliance-energy-card
// name: Lavatrice
// room: Lavanderia
// state_entity: binary_sensor.lavatrice_attiva
// energy_entity: sensor.lavatrice_e_asciugatrice_energy_a   (facoltativo, kWh totale)
//
// Config COMPLETA (per usarla anche senza l'integrazione, con helper manuali —
// ogni campo qui sotto sovrascrive quello che arriverebbe dagli attributi):
// power_entity: sensor.xxx_power_a
// price_entity: sensor.prezzo_energia_attuale     (usato solo se manca un cost_entity)
// cycles_day_entity: sensor.xxx_cicli_giorno
// cycles_week_entity: sensor.xxx_cicli_settimana
// cycles_month_entity: sensor.xxx_cicli_mese
// image_off: /local/lavatrice_oblo_vuoto.png
// image_on: /local/lavatrice_animata-18.gif

const FONT_LINK_ID = "aec-font-link";

class ApplianceEnergyCard extends HTMLElement {
  setConfig(config) {
    if (!config.state_entity) throw new Error("Serve 'state_entity' in configurazione.");
    if (!config.power_entity) throw new Error("Serve 'power_entity' in configurazione.");
    this._config = config;
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) {
      this._buildCard();
      this._built = true;
    }
    this._update();
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return {
      type: "custom:appliance-energy-card",
      name: "Nome elettrodomestico",
      room: "",
      state_entity: "",
      energy_entity: "",
      image_off: "",
      image_on: "",
    };
  }

  _num(entityId) {
    if (!entityId) return null;
    const st = this._hass.states[entityId];
    if (!st || st.state === "unknown" || st.state === "unavailable") return null;
    const n = parseFloat(st.state);
    return isNaN(n) ? null : n;
  }

  _fmtNum(n, decimals, fallback) {
    if (n === null || n === undefined) return fallback;
    return n.toLocaleString("it-IT", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  _ensureFont() {
    if (document.getElementById(FONT_LINK_ID)) return;
    const link = document.createElement("link");
    link.id = FONT_LINK_ID;
    link.rel = "stylesheet";
    link.href =
      "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap";
    document.head.appendChild(link);
  }

  _buildCard() {
    this._ensureFont();
    const cfg = this._config;

    const card = document.createElement("ha-card");
    card.style.padding = "0";
    card.style.background = "#171a20";
    card.style.border = "1px solid #2a2f38";
    card.style.borderRadius = "16px";
    card.style.overflow = "hidden";

    const root = document.createElement("div");
    root.className = "aec-root";
    root.innerHTML = `
      <style>
        .aec-root {
          --aec-panel: #1e222a;
          --aec-border: #2a2f38;
          --aec-text: #eef1f4;
          --aec-text-muted: #8b93a1;
          --aec-text-dim: #5b6270;
          --aec-on: #57d4c4;
          --aec-on-dim: rgba(87,212,196,0.16);
          --aec-power: #f0a860;
          --aec-cost: #9fc7ff;
          display: flex;
          gap: 16px;
          align-items: flex-start;
          padding: 16px;
          font-family: 'Inter', sans-serif;
          color: var(--aec-text);
        }
        .aec-figure {
          flex: 0 0 auto;
          width: 130px;
          height: 130px;
          border-radius: 14px;
          background: var(--aec-panel);
          border: 1px solid var(--aec-border);
          overflow: hidden;
          position: relative;
        }
        .aec-figure img { width: 100%; height: 100%; object-fit: cover; display: block; }
        .aec-dot {
          position: absolute; right: 7px; bottom: 7px;
          width: 9px; height: 9px; border-radius: 50%;
          background: #4a5261;
        }
        .aec-root.on .aec-dot { background: var(--aec-on); box-shadow: 0 0 0 4px var(--aec-on-dim); }
        .aec-body { flex: 1 1 auto; min-width: 0; }
        .aec-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
        .aec-name {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 15px; font-weight: 600; margin: 0; letter-spacing: -0.01em;
        }
        .aec-room { font-size: 12px; margin-top: 1px; color: var(--aec-text-dim); }
        .aec-pill {
          font-size: 11.5px; font-weight: 500; padding: 3px 9px 3px 7px;
          border-radius: 100px; background: var(--aec-panel); color: var(--aec-text-muted);
          white-space: nowrap; flex-shrink: 0; display: inline-flex; align-items: center; gap: 5px;
        }
        .aec-pill .sw { width: 6px; height: 6px; border-radius: 50%; background: #4a5261; }
        .aec-root.on .aec-pill { background: var(--aec-on-dim); color: var(--aec-on); }
        .aec-root.on .aec-pill .sw { background: var(--aec-on); }
        .aec-power-row { display: flex; align-items: baseline; gap: 6px; margin-top: 10px; }
        .aec-power-value {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 26px; font-weight: 600; color: var(--aec-text-dim); letter-spacing: -0.01em;
        }
        .aec-root.on .aec-power-value { color: var(--aec-power); }
        .aec-power-unit { font-size: 12.5px; color: var(--aec-text-dim); }

        .aec-cycles { margin-top: 12px; display: flex; flex-direction: column; gap: 4px; }
        .aec-cycle-row {
          display: flex; justify-content: space-between; align-items: baseline;
          font-size: 12.5px; color: var(--aec-text-muted);
          padding: 3px 0;
          border-bottom: 1px solid var(--aec-border);
        }
        .aec-cycle-row:last-child { border-bottom: none; }
        .aec-cycle-row .val {
          font-family: 'Space Grotesk', sans-serif;
          font-weight: 600; color: var(--aec-text); font-size: 13.5px;
        }

        .aec-energy-row {
          margin-top: 10px; display: flex; align-items: baseline; gap: 4px;
          font-size: 12.5px; color: var(--aec-text-muted);
        }
        .aec-energy-row .val {
          font-family: 'Space Grotesk', sans-serif;
          font-weight: 600; color: var(--aec-text); font-size: 14px;
        }
        .aec-cost-row { margin-top: 3px; font-size: 12px; color: var(--aec-cost); font-weight: 500; }
      </style>
      <div class="aec-figure">
        <img class="aec-img" src="" />
        <div class="aec-dot"></div>
      </div>
      <div class="aec-body">
        <div class="aec-top">
          <div>
            <p class="aec-name">${cfg.name || "Elettrodomestico"}</p>
            ${cfg.room ? `<p class="aec-room">${cfg.room}</p>` : ""}
          </div>
          <span class="aec-pill"><span class="sw"></span><span class="aec-status">Spento</span></span>
        </div>
        <div class="aec-power-row">
          <span class="aec-power-value aec-power">0</span>
          <span class="aec-power-unit">W adesso</span>
        </div>
        <div class="aec-cycles">
          <div class="aec-cycle-row"><span>Cicli oggi</span><span class="val aec-cycles-day">–</span></div>
          <div class="aec-cycle-row"><span>Cicli settimana</span><span class="val aec-cycles-week">–</span></div>
          <div class="aec-cycle-row"><span>Cicli mese</span><span class="val aec-cycles-month">–</span></div>
        </div>
        <div class="aec-energy-row">
          Consumo totale: <span class="val aec-energy">–</span> kWh
        </div>
        <div class="aec-cost-row">≈ € <span class="aec-cost">–</span> spesi finora</div>
      </div>
    `;
    card.appendChild(root);
    this.innerHTML = "";
    this.appendChild(card);

    this._root = root;
    this._img = root.querySelector(".aec-img");
    this._status = root.querySelector(".aec-status");
    this._power = root.querySelector(".aec-power");
    this._cyclesDay = root.querySelector(".aec-cycles-day");
    this._cyclesWeek = root.querySelector(".aec-cycles-week");
    this._cyclesMonth = root.querySelector(".aec-cycles-month");
    this._energy = root.querySelector(".aec-energy");
    this._cost = root.querySelector(".aec-cost");
  }

  _update() {
    const cfg = this._config;
    const stateEnt = this._hass.states[cfg.state_entity];
    const isOn = stateEnt && stateEnt.state === "on";
    const attrs = (stateEnt && stateEnt.attributes) || {};

    // La card preferisce sempre i valori scritti a mano in YAML (cfg.xxx);
    // se mancano, li legge dagli attributi che l'integrazione espone da sola
    // sul sensore principale (state_entity) — così basta una riga di YAML.
    const imageOff = cfg.image_off || attrs.image_off;
    const imageOn = cfg.image_on || attrs.image_on;
    const powerEntity = cfg.power_entity || attrs.power_entity;
    const cyclesDayEntity = cfg.cycles_day_entity || attrs.cycles_day_entity;
    const cyclesWeekEntity = cfg.cycles_week_entity || attrs.cycles_week_entity;
    const cyclesMonthEntity = cfg.cycles_month_entity || attrs.cycles_month_entity;
    const energyEntity = cfg.energy_entity;
    const costEntity = attrs.cost_entity;

    this._root.classList.toggle("on", isOn);
    this._status.textContent = isOn ? "In funzione" : "Spento";

    if (imageOn && imageOff) {
      this._img.src = isOn ? imageOn : imageOff;
    }

    const power = this._num(powerEntity);
    this._power.textContent = this._fmtNum(power, 0, "0");

    this._cyclesDay.textContent = this._fmtNum(this._num(cyclesDayEntity), 0, "–");
    this._cyclesWeek.textContent = this._fmtNum(this._num(cyclesWeekEntity), 0, "–");
    this._cyclesMonth.textContent = this._fmtNum(this._num(cyclesMonthEntity), 0, "–");

    const energy = this._num(energyEntity);
    this._energy.textContent = this._fmtNum(energy, 2, "–");

    // Il costo, se l'integrazione lo calcola già (sensore costo), viene letto direttamente da lì.
    const costFromEntity = this._num(costEntity);
    if (costFromEntity !== null) {
      this._cost.textContent = this._fmtNum(costFromEntity, 2, "–");
    } else {
      const price = this._num(cfg.price_entity);
      this._cost.textContent =
        energy !== null && price !== null ? this._fmtNum(energy * price, 2, "–") : "–";
    }
  }
}

customElements.define("appliance-energy-card", ApplianceEnergyCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "appliance-energy-card",
  name: "Appliance Energy Card",
  description: "Card per monitorare consumo, costo e cicli di un elettrodomestico",
});
