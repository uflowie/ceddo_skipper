# test_model.py
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models

# 1. Same preprocessing as training
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# 2. Load test set
test_data   = datasets.ImageFolder("data/test", transform=transform)
test_loader = DataLoader(test_data, batch_size=32, shuffle=False)

# 3. Re-create the model architecture and load weights
device = "cuda" if torch.cuda.is_available() else "cpu"
model = models.resnet18()
model.fc = nn.Linear(model.fc.in_features, 1)
model.load_state_dict(torch.load("trained_model.pth", map_location=device))
model.to(device)
model.eval()

# 4. Evaluate
correct, total = 0, 0
with torch.no_grad():
    for imgs, labels in test_loader:
        imgs, labels = imgs.to(device), labels.to(device)
        logits = model(imgs).squeeze(1)          # [B]  (raw scores)
        preds  = (torch.sigmoid(logits) > 0.5)   # boolean → 0/1
        correct += (preds == labels).sum().item()
        total   += labels.size(0)

print(f"Test accuracy: {100 * correct / total:.2f}%")
