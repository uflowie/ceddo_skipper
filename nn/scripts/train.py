import sys
import os
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision import datasets, transforms, models
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please install required packages with: pip install torch torchvision")
    input("Press Enter to exit...")
    sys.exit(1)

# 1. Transforms (resize all images to same size, normalize)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

# 2. Dataset (assuming folder structure: root/class_name/images)
if not os.path.exists("data/train"):
    print("Error: Training data directory 'data/train' not found!")
    print("Please ensure you have the training data in the correct structure:")
    print("  data/train/yes/  (images where commentary should be skipped)")
    print("  data/train/no/   (images where commentary should NOT be skipped)")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    train_data = datasets.ImageFolder("data/train", transform=transform)
    if len(train_data) == 0:
        print("Error: No training images found in data/train directory!")
        input("Press Enter to exit...")
        sys.exit(1)
    train_loader = DataLoader(train_data, batch_size=32, shuffle=True)
    print(f"Loaded {len(train_data)} training images")
except Exception as e:
    print(f"Error loading training data: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

# 3. Simple model (use pretrained resnet18, change last layer to binary output)
print("Loading model...")
try:
    model = models.resnet18(pretrained=True)
    model.fc = nn.Linear(model.fc.in_features, 1)   # Binary classifier (single logit)
except Exception as e:
    print(f"Error loading model: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

# 4. Loss & optimizer
criterion = nn.BCEWithLogitsLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

# 5. Training loop
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
model.to(device)

print("Starting training...")
try:
    for epoch in range(5):
        epoch_loss = 0
        batch_count = 0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.float().to(device)
            optimizer.zero_grad()
            outputs = model(imgs).squeeze(1)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            batch_count += 1
        
        avg_loss = epoch_loss / batch_count
        print(f"Epoch {epoch+1}/5: Average Loss={avg_loss:.4f}")
    
    print("Training completed successfully!")
    
    # Save the model
    torch.save(model.state_dict(), "trained_model.pth")
    print("Model saved as 'trained_model.pth'")
    
except Exception as e:
    print(f"Error during training: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

print("Script completed. Press Enter to exit...")
input()
