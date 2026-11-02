# PULSE Troubleshooting & FAQ

## 1. Backend Port Already in Use (Port 8000)
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
```

## 2. Frontend Port Collision (Port 5173)
Vite will automatically increment to 5174 or 5175 if port 5173 is occupied.

## 3. Bio_ClinicalBERT Checkpoint Missing
If the fine-tuned checkpoint is missing, run:
```bash
python scripts/train_production_clinicalbert.py --epochs 3 --synthetic 160 --trainable-last-n 2
```
