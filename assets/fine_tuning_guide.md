## Wired-to-Wireless RSSI Emulation & Calibration
Frequency Range: 220 MHz, 429 MHz, 920 MHz
Scope: 0-10 Meters (Near-to-Mid Field)

### 1. Overview
The goal of this method is to use a Wired Setup (Coaxial Cables + Variable Attenuator) to predict the Wireless RSSI of an ideal outdoor environment where the First Fresnel Zone (FFZ) is completely clear.

### 2. Theoretical Foundation
To make the wired signal equivalent to the wireless signal at distance d, the Attenuator (VATT) must account for Free Space Path Loss (FSPL) while compensating for the absence of physical antennas.

The Master Equation:
$$
VATT_{\rm{setting}}=FSPL(d,f)-(G_{\rm{TX}}+G_{\rm{RX}})-L_{\rm{cable}}
$$

* $FSPL(d,f)$: Free Space Path Loss at distance $d$ and frequency $f$.
* $G_{\rm{TX}}+G_{\rm{RX}}$: Combined Gain of your antennas (dBi). **Crucial: You must subtract this because the wired setup bypasses the antenna's physical amplification.**
* $L_{\rm{cable}}$: Insertion loss of the coaxial cables and connectors in your test bench.

### 3. Reference Table: Optimal Benchmarking Points
For outdoor validation, use these "Golden Points" where the wireless signal is most stable and closest to the theoretical model.

| Frequency<br />($f$) | Wavelength<br />($\lambda$) | Recom. Dist.<br />($d$) | Mini. Height<br />($h$) | $FSPL$ at 1 M<br />($FSPL_0$) |
| :--------------------: | :---------------------------: | :-----------------------: | :-----------------------: | :-------------------------------: |
|        220 MHz        |            1.36 m            |           5.0 m           |          > 2.5 m          |              19.3 dB              |
|        429 MHz        |            0.70 m            |           3.0 m           |          > 1.8 m          |              25.1 dB              |
|        920 MHz        |            0.33 m            |           2.0 m           |          > 1.5 m          |              31.7 dB              |

### 4. Operational Steps
#### Step A: Indoor Wired Setup (Ground Truth)
1. Connect the Transmitter (TX) to the Receiver (RX) using:
[TX] -> [Cable 1] -> [Step Attenuator (VATT)] -> [Cable 2] -> [RX]
2. Calculate the target $FSPL(d)$ for your desired distance.
$FSPL(d)=FSPL_0+20\log_{10}(d)$
3. Adjust the VATT using the Master Equation in Section 2.
4. Record the resulting RSSI. This is your **Predicted Ideal RSSI** for distance $d$.

#### Step B: Outdoor Wireless Validation
1. Mount antennas on non-metallic stands (PVC or Wood).
2. Set the height ($h$) according to the Reference Table to clear the First Fresnel Zone.
3. Ensure the polarization (Vertical/Horizontal) is identical for both ends.
4. Measure RSSI at the same distance $d$.
5. Comparison: If $RSSI_{\rm{Wireless}}\approx RSSI_{\rm{Wired}}$, your prediction model is calibrated.

### 5. Critical Constraints & Troubleshooting
* **The 220MHz Height Rule:** At 220MHz, the wavelength is long (∼1.36m). If your antenna is lower than 2m, ground reflections will cause "multi-path fading," making your wireless RSSI significantly lower than the wired prediction.
* **Near-Field Warning:** Do not attempt wireless benchmarking at $d<1$ meter for these frequencies. The antennas are in the "induction near-field," where gain values are inconsistent.
* **Cable Loss Calibration:** Always measure your cable loss ($L_{\rm{cable}}$​) at the specific frequency before starting, as it increases with frequency (e.g., loss at 920MHz is higher than at 220MHz).