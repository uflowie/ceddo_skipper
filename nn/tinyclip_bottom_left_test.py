import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import os
import numpy as np
import json
from pathlib import Path
import random

class TinyCLIPBottomLeftTest:
    def __init__(self):
        print("Loading CLIP model...")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        print(f"Model loaded on {self.device}")
        
    def crop_bottom_left(self, image):
        """
        Crop the bottom-left corner of the image
        Treating image as 5 wide x 4 high grid, take bottom-left cell
        """
        width, height = image.size
        
        # Calculate grid dimensions
        grid_width = width // 5
        grid_height = height // 4
        
        # Bottom-left corner coordinates
        # Bottom row (4th row, 0-indexed as row 3), left column (0th column)
        left = 0
        top = height - grid_height  # Start from bottom
        right = grid_width
        bottom = height
        
        cropped = image.crop((left, top, right, bottom))
        return cropped
        
    def analyze_sample_batch(self, sample_size=50, crop_mode="bottom_left"):
        """
        Quick analysis with a small sample of images
        crop_mode: "full", "bottom_left", or "both"
        """
        
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
            
            class_results = {}
            
            # Process different crop modes
            modes_to_test = ["full", "bottom_left"] if crop_mode == "both" else [crop_mode]
            
            for mode in modes_to_test:
                print(f"  Processing with {mode} image...")
                
                # Load and process images
                images = []
                valid_files = []
                
                for img_path in image_files:
                    try:
                        image = Image.open(img_path).convert('RGB')
                        
                        # Apply cropping based on mode
                        if mode == "bottom_left":
                            image = self.crop_bottom_left(image)
                        # mode == "full" uses original image
                        
                        images.append(image)
                        valid_files.append(img_path.name)
                    except Exception as e:
                        print(f"    Error loading {img_path}: {e}")
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
                mode_results = {}
                for idx, query in enumerate(text_queries):
                    query_sims = similarities[:, idx]
                    
                    mode_results[query] = {
                        "mean": float(query_sims.mean()),
                        "std": float(query_sims.std()),
                        "min": float(query_sims.min()),
                        "max": float(query_sims.max()),
                        "median": float(np.median(query_sims))
                    }
                    
                    # Find top matches
                    top_indices = np.argsort(query_sims)[::-1][:5]
                    mode_results[query]["top_matches"] = [
                        {"image": valid_files[i], "similarity": float(query_sims[i])}
                        for i in top_indices
                    ]
                
                class_results[mode] = {
                    "num_samples": len(valid_files),
                    "queries": mode_results
                }
                
                print(f"    Completed {mode} analysis")
            
            results[class_name] = class_results
        
        return results, text_queries

def main():
    print("TinyCLIP Bottom-Left Crop Test")
    print("=" * 50)
    print("Testing CLIP embeddings on bottom-left corner of images")
    print("(treating each image as 5x4 grid, analyzing bottom-left cell)")
    print()
    
    try:
        analyzer = TinyCLIPBottomLeftTest()
        
        # Test both full images and bottom-left crops
        results, text_queries = analyzer.analyze_sample_batch(sample_size=30, crop_mode="both")
        
        # Display results
        print("\n" + "="*80)
        print("RESULTS COMPARISON: FULL IMAGE vs BOTTOM-LEFT CROP")
        print("="*80)
        
        for query in text_queries:
            print(f"\nQuery: '{query}'")
            print("-" * 50)
            
            # Compare results for each class
            for class_name in ["yes", "no"]:
                if class_name in results:
                    print(f"\n{class_name.upper()} class:")
                    
                    for mode in ["full", "bottom_left"]:
                        if mode in results[class_name]:
                            stats = results[class_name][mode]["queries"][query]
                            print(f"  {mode.upper()} IMAGE:")
                            print(f"    Mean similarity: {stats['mean']:.4f} ± {stats['std']:.4f}")
                            print(f"    Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
                            print(f"    Top match: {stats['top_matches'][0]['image']} (sim: {stats['top_matches'][0]['similarity']:.4f})")
                    
                    # Calculate improvement from cropping
                    if "full" in results[class_name] and "bottom_left" in results[class_name]:
                        full_mean = results[class_name]["full"]["queries"][query]["mean"]
                        crop_mean = results[class_name]["bottom_left"]["queries"][query]["mean"]
                        improvement = crop_mean - full_mean
                        
                        print(f"  IMPROVEMENT FROM CROPPING: {improvement:+.4f}")
                        if improvement > 0:
                            print(f"    -> Bottom-left crop is MORE similar to '{query}'")
                        else:
                            print(f"    -> Full image is MORE similar to '{query}'")
        
        # Overall comparison
        print("\n" + "="*80)
        print("OVERALL ANALYSIS:")
        print("="*80)
        
        for query in text_queries:
            print(f"\nQuery: '{query}'")
            print("-" * 30)
            
            if "yes" in results and "no" in results:
                for mode in ["full", "bottom_left"]:
                    if mode in results["yes"] and mode in results["no"]:
                        yes_mean = results["yes"][mode]["queries"][query]["mean"]
                        no_mean = results["no"][mode]["queries"][query]["mean"]
                        difference = no_mean - yes_mean  # NO should be higher for "first dates"
                        
                        print(f"{mode.upper()} IMAGE:")
                        print(f"  NO class mean:  {no_mean:.4f}")
                        print(f"  YES class mean: {yes_mean:.4f}")
                        print(f"  Difference (NO-YES): {difference:+.4f}")
                        
                        if difference > 0:
                            print(f"  -> NO class more similar (CORRECT for 'first dates')")
                        else:
                            print(f"  -> YES class more similar (unexpected)")
                        print()
        
        # Save results
        output_file = "tinyclip_bottom_left_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Detailed results saved to: {output_file}")
        
        print("\n" + "="*80)
        print("CROPPING EFFECTIVENESS SUMMARY:")
        print("="*80)
        print("Check if bottom-left cropping improves the distinction between classes.")
        print("Look for larger differences between NO and YES classes with cropping.")
        print("This could indicate that the 'first dates' content is concentrated")
        print("in the bottom-left area of the images.")
        
        print("\nBottom-left crop test completed successfully!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()