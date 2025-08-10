import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import os
import numpy as np
import json
from pathlib import Path
import random

class QuickTinyCLIPTest:
    def __init__(self):
        print("Loading CLIP model...")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        print(f"Model loaded on {self.device}")
        
    def analyze_sample_batch(self, sample_size=50):
        """Quick analysis with a small sample of images"""
        
        # Text queries to test
        text_queries = ["first dates", "first dates logo"]
        
        # Get text embeddings
        print("Getting text embeddings...")
        inputs = self.processor(text=text_queries, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = F.normalize(text_features, p=2, dim=-1)
        
        # Data paths
        base_path = Path("data")
        train_path = base_path / "train"
        
        results = {}
        
        # Analyze each class
        for class_name in ["yes", "no"]:
            class_path = train_path / class_name
            if not class_path.exists():
                print(f"Warning: {class_path} does not exist")
                continue
                
            # Get all image files and sample randomly
            image_files = list(class_path.glob("*.png")) + list(class_path.glob("*.jpg"))
            if len(image_files) > sample_size:
                image_files = random.sample(image_files, sample_size)
            
            print(f"Processing {len(image_files)} sample images from {class_name} class...")
            
            # Load and process images
            images = []
            valid_files = []
            
            for img_path in image_files:
                try:
                    image = Image.open(img_path).convert('RGB')
                    images.append(image)
                    valid_files.append(img_path.name)
                except Exception as e:
                    print(f"Error loading {img_path}: {e}")
                    continue
            
            if not images:
                continue
                
            # Get image embeddings
            inputs = self.processor(images=images, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                image_features = F.normalize(image_features, p=2, dim=-1)
            
            # Compute similarities
            similarities = torch.mm(image_features, text_features.t())
            similarities = similarities.cpu().numpy()
            
            # Calculate statistics for each text query
            class_results = {}
            for idx, query in enumerate(text_queries):
                query_sims = similarities[:, idx]
                
                class_results[query] = {
                    "mean": float(query_sims.mean()),
                    "std": float(query_sims.std()),
                    "min": float(query_sims.min()),
                    "max": float(query_sims.max()),
                    "median": float(np.median(query_sims))
                }
                
                # Find top matches
                top_indices = np.argsort(query_sims)[::-1][:5]
                class_results[query]["top_matches"] = [
                    {"image": valid_files[i], "similarity": float(query_sims[i])}
                    for i in top_indices
                ]
            
            results[class_name] = {
                "num_samples": len(valid_files),
                "queries": class_results
            }
            
            print(f"  Completed {class_name} class analysis")
        
        return results, text_queries

def main():
    print("Quick TinyCLIP Test for Binary Classification")
    print("=" * 50)
    print("Testing CLIP embeddings for 'first dates' and 'first dates logo'")
    print("against sample images from YES/NO training data...\n")
    
    try:
        analyzer = QuickTinyCLIPTest()
        results, text_queries = analyzer.analyze_sample_batch(sample_size=30)
        
        # Display results
        print("\n" + "="*60)
        print("RESULTS SUMMARY:")
        print("="*60)
        
        for query in text_queries:
            print(f"\nQuery: '{query}'")
            print("-" * 40)
            
            for class_name in ["yes", "no"]:
                if class_name in results:
                    stats = results[class_name]["queries"][query]
                    print(f"{class_name.upper()} class ({results[class_name]['num_samples']} samples):")
                    print(f"  Mean similarity: {stats['mean']:.4f} ± {stats['std']:.4f}")
                    print(f"  Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
                    print(f"  Median: {stats['median']:.4f}")
                    
                    print(f"  Top 3 matches:")
                    for i, match in enumerate(stats["top_matches"][:3], 1):
                        print(f"    {i}. {match['image']} (sim: {match['similarity']:.4f})")
                    print()
        
        # Compare classes
        print("\n" + "="*60)
        print("CLASS COMPARISON:")
        print("="*60)
        
        if "yes" in results and "no" in results:
            for query in text_queries:
                yes_mean = results["yes"]["queries"][query]["mean"]
                no_mean = results["no"]["queries"][query]["mean"]
                difference = yes_mean - no_mean
                
                print(f"\nQuery: '{query}'")
                print(f"  YES class mean: {yes_mean:.4f}")
                print(f"  NO class mean:  {no_mean:.4f}")
                print(f"  Difference:     {difference:.4f}")
                
                if abs(difference) > 0.01:  # Threshold for meaningful difference
                    if difference > 0:
                        print(f"  → YES class is MORE similar to '{query}' (difference: +{difference:.4f})")
                    else:
                        print(f"  → NO class is MORE similar to '{query}' (difference: {difference:.4f})")
                else:
                    print(f"  → Classes are similarly matched to '{query}'")
        
        # Save results
        output_file = "tinyclip_quick_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to: {output_file}")
        
        print("\n" + "="*60)
        print("INTERPRETATION:")
        print("="*60)
        print("- Higher similarity scores indicate better matches")
        print("- A clear difference between YES/NO classes suggests CLIP can distinguish them")
        print("- Look for which text query ('first dates' vs 'first dates logo') works better")
        print("- Consider the top matches to understand what CLIP is detecting")
        
        print("\nQuick test completed successfully!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()