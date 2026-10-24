# Figures for the proposal

- `funnel.py` draws `funnel.png`: the harness as a funnel. The whole corpus is
  coded by the model with the frozen codebook; a calibration loop and held-out
  test sit beside it; the narrow anomaly residue is coded abductively by people.
  It shows the design argument, so it belongs in the proposal. The technical
  document uses a plain block diagram instead (`../source/flow.py`).

```bash
python funnel.py funnel.png
```
