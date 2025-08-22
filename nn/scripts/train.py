import sys
import os
import argparse
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision import datasets, transforms
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please install required packages with: pip install torch torchvision")
    input("Press Enter to exit...")
    sys.exit(1)

from models import get_model

def main():
    parser = argparse.ArgumentParser(description='Train models for ceddo skipper')
    parser.add_argument('model_name', help='Model to train (mobilenet, mobilenetv4, resnet18)')
    parser.add_argument('output_file', help='Output ONNX file name')
    parser.add_argument('--epochs', type=int, default=5, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-3, help='Learning rate')
    
    args = parser.parse_args()
    
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
        train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True)
        print(f"Loaded {len(train_data)} training images")
    except Exception as e:
        print(f"Error loading training data: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # 3. Load model
    print(f"Loading {args.model_name} model...")
    try:
        model, model_info = get_model(args.model_name)
        print(f"Model architecture: {model_info['name']}")
        print(f"Input size: {model_info['input_size']}")
        print(f"Output: {model_info['output_description']}")
    except Exception as e:
        print(f"Error loading model: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # 4. Loss & optimizer
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    
    # 5. Training loop
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    model.to(device)
    
    print(f"Starting training with {model_info['name']}...")
    try:
        for epoch in range(args.epochs):
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
            print(f"Epoch {epoch+1}/{args.epochs}: Average Loss={avg_loss:.4f}, Accuracy={accuracy:.2f}%")
        
        print("Training completed successfully!")
        
        # Save the PyTorch model (.pth)
        pth_filename = args.output_file.replace('.onnx', '.pth')
        torch.save(model.state_dict(), pth_filename)
        print(f"PyTorch model saved as '{pth_filename}'")
        
        # Export to ONNX
        print("Exporting model to ONNX...")
        model.eval()
        dummy_input = torch.randn(1, 3, 224, 224).to(device)
        
        try:
            torch.onnx.export(
                model,
                dummy_input,
                args.output_file,
                export_params=True,
                opset_version=11,
                input_names=['input'],
                output_names=['output'],
                dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
            )
            print(f"ONNX model saved as '{args.output_file}'")
        except Exception as e:
            print(f"Error exporting to ONNX: {e}")
            print("PyTorch model was saved successfully, but ONNX export failed")
        
        # Save model info for reference
        info_filename = args.output_file.replace('.onnx', '_info.txt')
        with open(info_filename, "w") as f:
            f.write(f"Model: {model_info['name']}\n")
            if 'model_identifier' in model_info:
                f.write(f"Model identifier: {model_info['model_identifier']}\n")
            f.write(f"Input size: {model_info['input_size']}\n")
            f.write(f"Output: {model_info['output_description']}\n")
            f.write(f"Training epochs: {args.epochs}\n")
            f.write(f"Final accuracy: {accuracy:.2f}%\n")
            if 'framework' in model_info:
                f.write(f"Framework: {model_info['framework']}\n")
            if 'architecture_details' in model_info:
                f.write(f"Architecture details:\n{model_info['architecture_details']}\n")
        
        print(f"Model info saved to '{info_filename}'")
        
    except Exception as e:
        print(f"Error during training: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    print("Script completed. Press Enter to exit...")
    input()

if __name__ == "__main__":
    main()