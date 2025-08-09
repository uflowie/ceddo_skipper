import sys
import os
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision import datasets, transforms
    import timm
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please install required packages with: pip install torch torchvision timm")
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

# 3. MobileNetV4 Small model (use pretrained from timm)
print("Loading MobileNetV4 Small model from timm...")
try:
    model = timm.create_model('mobilenetv4_conv_small.e2400_r224_in1k', pretrained=True, num_classes=1)
    
    print(f"Model architecture: MobileNetV4 Small")
    print(f"Input size: 224x224")
    print(f"Output classes: 1 (binary classification)")
    
except Exception as e:
    print(f"Error loading model: {e}")
    print("Make sure timm is installed and supports MobileNetV4 Small")
    input("Press Enter to exit...")
    sys.exit(1)

# 4. Loss & optimizer
criterion = nn.BCEWithLogitsLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

# 5. Training loop
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
model.to(device)

print("Starting training with MobileNetV4 Small...")
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
    
    # Save the PyTorch model (.pth)
    print("Saving PyTorch model...")
    torch.save(model.state_dict(), "trained_model_mobilenetv4.pth")
    print("PyTorch model saved as 'trained_model_mobilenetv4.pth'")
    
    # Export to ONNX
    print("Exporting model to ONNX...")
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224).to(device)
    
    try:
        torch.onnx.export(
            model,
            dummy_input,
            "trained_model_mobilenetv4.onnx",
            export_params=True,
            opset_version=11,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
        )
        print("ONNX model saved as 'trained_model_mobilenetv4.onnx'")
    except Exception as e:
        print(f"Error exporting to ONNX: {e}")
        print("PyTorch model was saved successfully, but ONNX export failed")
    
    # Save model info for reference
    with open("model_info_mobilenetv4.txt", "w") as f:
        f.write("Model: MobileNetV4 Small (timm)\n")
        f.write(f"Model name: mobilenetv4_conv_small.e2400_r224_in1k\n")
        f.write(f"Input size: 224x224\n")
        f.write(f"Output: Single logit (binary classification)\n")
        f.write(f"Training epochs: 5\n")
        f.write(f"Final accuracy: {accuracy:.2f}%\n")
        f.write(f"Pretrained: Yes\n")
        f.write(f"Framework: timm\n")
    
    print("Model info saved to 'model_info_mobilenetv4.txt'")
    
except Exception as e:
    print(f"Error during training: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

print("Script completed. Press Enter to exit...")
input()