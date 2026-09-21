# Card Elettrodomestici

Integrazione custom per Home Assistant che monitora un elettrodomestico (lavatrice, asciugatrice, lavastoviglie, ecc.) partendo da un sensore di potenza già esistente: rileva quando è in funzione, conta i cicli, calcola il consumo e il costo — con una card Lovelace dedicata per vederlo tutto in un colpo d'occhio.

Nato per risolvere un problema concreto: i normali "sensori di soglia" di Home Assistant scattano istantaneamente, quindi un calo di potenza temporaneo (es. la lavastoviglie che scende a 0 W mentre carica l'acqua) viene contato come un ciclo finito + uno nuovo. Questa integrazione applica un ritardo di spegnimento configurabile prima di considerare l'elettrodomestico davvero spento, eliminando i falsi positivi.

![Anteprima della card](docs/screenshot-card.png)
*(sostituisci con uno screenshot reale della tua dashboard)*

## Caratteristiche

- **Rilevamento accensione/spegnimento con debounce reale**, gestito lato integrazione (Python), non con automazioni sparse
- **Conteggio cicli** giorno / settimana / mese, con reset automatico al cambio periodo — sopravvive ai riavvii di Home Assistant
- **Costo stimato in tempo reale**, calcolato come consumo totale (kWh) × prezzo attuale (€/kWh) da un sensore prezzo a scelta (es. PUN)
- **Card Lovelace dedicata**, con immagine statica quando spento e GIF animata quando in funzione, cicli e consumo ben leggibili
- Configurazione interamente da interfaccia grafica (config flow), nessun file YAML da editare

## Screenshot

| Spento | In funzione |
|---|---|
| ![off](docs/screenshot-off.png) | ![on](docs/screenshot-on.png) |

## Installazione

### Tramite HACS (consigliato)
1. HACS > Integrazioni > ⋮ > Repository personalizzati
2. Aggiungi questo repository come tipo "Integrazione"
3. Cerca **"Card Elettrodomestici"** in HACS e installa
4. Riavvia Home Assistant

### Manuale
1. Copia la cartella `custom_components/card_elettrodomestici` dentro `config/custom_components/` della tua installazione
2. Riavvia Home Assistant

## Configurazione

Impostazioni > Dispositivi e servizi > **+ Aggiungi integrazione** > cerca **"Card Elettrodomestici"**.

| Campo | Descrizione | Obbligatorio |
|---|---|---|
| Nome | Nome dell'elettrodomestico (es. "Lavatrice") | Sì |
| Sensore di potenza | Entità `sensor` in Watt che misura la potenza istantanea | Sì |
| Sensore di energia totale | Entità `sensor` in kWh, se disponibile (usato per il calcolo del costo) | No |
| Sensore prezzo attuale | Entità `sensor` in €/kWh (es. da PUN) | No |
| Soglia accensione | Potenza (W) sopra la quale l'elettrodomestico è considerato attivo | Sì (default 15 W) |
| Ritardo spegnimento | Secondi di potenza sotto soglia richiesti prima di considerarlo spento | Sì (default 180 s) |

Puoi aggiungere più elettrodomestici ripetendo la procedura una volta per ciascuno.

## Entità create

Per ogni elettrodomestico configurato:

- `binary_sensor.<nome>_attiva` — acceso/spento, con debounce
- `sensor.<nome>_cicli_oggi`
- `sensor.<nome>_cicli_settimana`
- `sensor.<nome>_cicli_mese`
- `sensor.<nome>_costo_stimato` — solo se hai indicato sensore energia e sensore prezzo

## Card Lovelace

```yaml
type: custom:appliance-energy-card
name: Lavatrice
room: Lavanderia
state_entity: binary_sensor.lavatrice_attiva
power_entity: sensor.lavatrice_e_asciugatrice_power_a
cycles_day_entity: sensor.lavatrice_cicli_oggi
cycles_week_entity: sensor.lavatrice_cicli_settimana
cycles_month_entity: sensor.lavatrice_cicli_mese
energy_entity: sensor.lavatrice_e_asciugatrice_energy_a
price_entity: sensor.prezzo_energia_attuale
image_off: /local/lavatrice_oblo_vuoto.png
image_on: /local/lavatrice_animata-18.gif
```

La card viene caricata automaticamente dall'integrazione stessa (nessun file da copiare in `www/`, nessuna risorsa da registrare a mano): appena installi "Card Elettrodomestici", la card `custom:appliance-energy-card` è già disponibile.

## Roadmap

- [ ] Traduzione inglese completa
- [ ] Editor visuale per la configurazione della card (non solo YAML)
- [ ] Supporto nativo alla Dashboard Energia di Home Assistant
- [ ] Statistiche storiche (grafico consumo nel tempo)

## Licenza

MIT
