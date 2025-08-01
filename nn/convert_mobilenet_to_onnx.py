import sys
import os
try:
    import torch
    import torch.nn as nn
    from torchvision import models
    import onnx
    import onnxruntime as ort
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please install required packages with: pip install torch torchvision onnx onnxruntime")
    input("Press Enter to exit...")
    sys.exit(1)

# Check if trained model exists
if not os.path.exists("trained_model_mobilenet.pth"):
    print("Error: trained_model_mobilenet.pth not found!")
    print("Please make sure you have trained the MobileNetV3 model first using train_mobilenet.py")
    input("Press Enter to exit...")
    sys.exit(1)

print("Loading trained MobileNetV3 model...")
try:
    # Recreate the model architecture (same as in train_mobilenet.py)
    model = models.mobilenet_v3_small(weights=None)  # No pretrained weights needed for conversion
    
    # Replace the classifier with the same architecture used in training
    model.classifier = nn.Sequential(
        nn.Linear(model.classifier[0].in_features, 1024),
        nn.Hardswish(inplace=True),
        nn.Dropout(0.2, inplace=True),
        nn.Linear(1024, 1)  # Binary classifier (single logit)
    )
    
    # Load the trained weights
    model.load_state_dict(torch.load("trained_model_mobilenet.pth", map_location="cpu"))
    model.eval()
    
    print("MobileNetV3 model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

print("Converting MobileNetV3 to ONNX format...")
try:
    # Create dummy input for tracing (224x224 RGB image)
    dummy_input = torch.randn(1, 3, 224, 224)
    
    # Export to ONNX
    torch.onnx.export(
        model,
        dummy_input,
        "trained_model_mobilenet.onnx",
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size'},
                     'output': {0: 'batch_size'}}
    )
    
    print("ONNX model exported successfully!")
    
    # Verify the ONNX model
    onnx_model = onnx.load("trained_model_mobilenet.onnx")
    onnx.checker.check_model(onnx_model)
    print("ONNX model verification passed!")
    
    # Test inference
    ort_session = ort.InferenceSession("trained_model_mobilenet.onnx")
    ort_inputs = {ort_session.get_inputs()[0].name: dummy_input.numpy()}
    ort_outs = ort_session.run(None, ort_inputs)
    
    # Compare PyTorch and ONNX outputs
    with torch.no_grad():
        torch_out = model(dummy_input)
    
    print(f"PyTorch output: {torch_out.item():.6f}")
    print(f"ONNX output: {ort_outs[0][0][0]:.6f}")
    print(f"Difference: {abs(torch_out.item() - ort_outs[0][0][0]):.6f}")
    
    if abs(torch_out.item() - ort_outs[0][0][0]) < 1e-5:
        print("✓ Conversion successful! Outputs match.")
    else:
        print("⚠ Warning: Outputs don't match exactly, but this might be acceptable.")
    
except Exception as e:
    print(f"Error during ONNX conversion: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

print("\nConversion completed!")
print("Files created:")
print("- trained_model_mobilenet.onnx (for use in browser)")
print("\nYou can now use the MobileNetV3 ONNX model in your content script.")
input("Press Enter to exit...")