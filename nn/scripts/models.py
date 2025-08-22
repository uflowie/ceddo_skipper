import torch
import torch.nn as nn
from torchvision import models

def get_model(model_name):
    """
    Get a model and its configuration based on the model name.
    
    Args:
        model_name (str): Name of the model to load
        
    Returns:
        tuple: (model, model_info) where model_info is a dict with model details
    """
    model_name = model_name.lower()
    
    if model_name == "resnet18":
        return get_resnet18()
    elif model_name == "mobilenet":
        return get_mobilenet()
    elif model_name == "mobilenetv4":
        return get_mobilenetv4()
    else:
        raise ValueError(f"Unknown model: {model_name}. Supported models: resnet18, mobilenet, mobilenetv4")

def get_resnet18():
    """Get ResNet18 model with binary classification head."""
    model = models.resnet18(pretrained=True)
    model.fc = nn.Linear(model.fc.in_features, 1)
    
    model_info = {
        'name': 'ResNet18',
        'input_size': '224x224',
        'output_description': 'Single logit (binary classification)',
        'framework': 'torchvision',
        'architecture_details': f"  Linear({model.fc.in_features} -> 1)"
    }
    
    return model, model_info

def get_mobilenet():
    """Get MobileNetV3 Small model with binary classification head."""
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    
    # Replace the classifier with a binary classifier
    original_in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(original_in_features, 1024),
        nn.Hardswish(inplace=True),
        nn.Dropout(0.2, inplace=True),
        nn.Linear(1024, 1)
    )
    
    model_info = {
        'name': 'MobileNetV3-Small',
        'input_size': '224x224',
        'output_description': 'Single logit (binary classification)',
        'framework': 'torchvision',
        'architecture_details': f"  Linear({original_in_features} -> 1024)\n  Hardswish()\n  Dropout(0.2)\n  Linear(1024 -> 1)"
    }
    
    return model, model_info

def get_mobilenetv4():
    """Get MobileNetV4 Small model with binary classification head."""
    try:
        import timm
    except ImportError:
        raise ImportError("timm is required for MobileNetV4. Install with: pip install timm")
    
    model = timm.create_model('mobilenetv4_conv_small.e2400_r224_in1k', pretrained=True, num_classes=1)
    
    model_info = {
        'name': 'MobileNetV4 Small',
        'model_identifier': 'mobilenetv4_conv_small.e2400_r224_in1k',
        'input_size': '224x224',
        'output_description': 'Single logit (binary classification)',
        'framework': 'timm'
    }
    
    return model, model_info