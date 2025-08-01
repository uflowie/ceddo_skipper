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

# 3. MobileNetV3 model (use pretrained mobilenet_v3_small, change last layer to binary output)
print("Loading MobileNetV3 model...")
try:
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    
    # Replace the classifier with a binary classifier
    # MobileNetV3 has a 'classifier' attribute with a sequential layer
    model.classifier = nn.Sequential(
        nn.Linear(model.classifier[0].in_features, 1024),
        nn.Hardswish(inplace=True),
        nn.Dropout(0.2, inplace=True),
        nn.Linear(1024, 1)  # Binary classifier (single logit)
    )
    
    print(f"Model architecture: MobileNetV3-Small")
    print(f"Classifier input features: {model.classifier[0].in_features}")
    
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

print("Starting training with MobileNetV3...")
try:
    for epoch in range(5):
        epoch_loss = 0
        batch_count = 0
        correct_predictions = 0
        total_samples = 0
        
        model.train()
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.float().to(device)
            
            optimizer.zero_grad()
            outputs = model(imgs).squeeze(1)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            # Calculate accuracy
            predictions = (torch.sigmoid(outputs) > 0.5).float()
            correct_predictions += (predictions == labels).sum().item()
            total_samples += labels.size(0)
            
            epoch_loss += loss.item()
            batch_count += 1
        
        avg_loss = epoch_loss / batch_count
        accuracy = correct_predictions / total_samples * 100
        print(f"Epoch {epoch+1}/5: Average Loss={avg_loss:.4f}, Accuracy={accuracy:.2f}%")
    
    print("Training completed successfully!")
    
    # Save the model
    torch.save(model.state_dict(), "trained_model_mobilenet.pth")
    print("Model saved as 'trained_model_mobilenet.pth'")
    
    # Save model info for reference
    with open("model_info_mobilenet.txt", "w") as f:
        f.write("Model: MobileNetV3-Small\n")
        f.write(f"Input size: 224x224\n")
        f.write(f"Output: Single logit (binary classification)\n")
        f.write(f"Training epochs: 5\n")
        f.write(f"Final accuracy: {accuracy:.2f}%\n")
        f.write(f"Classifier architecture:\n")
        f.write(f"  Linear({model.classifier[0].in_features} -> 1024)\n")
        f.write(f"  Hardswish()\n")
        f.write(f"  Dropout(0.2)\n")
        f.write(f"  Linear(1024 -> 1)\n")
    
    print("Model info saved to 'model_info_mobilenet.txt'")
    
except Exception as e:
    print(f"Error during training: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

print("Script completed. Press Enter to exit...")
input()