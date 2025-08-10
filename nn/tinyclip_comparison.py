import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import os
import numpy as np
import json
from pathlib import Path

class TinyCLIPComparator:
    def __init__(self):
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
    def get_text_embeddings(self, texts):
        """Get embeddings for text prompts"""
        inputs = self.processor(text=texts, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = F.normalize(text_features, p=2, dim=-1)
        
        return text_features
    
    def get_image_embeddings(self, image_paths):
        """Get embeddings for image files"""
        images = []
        valid_paths = []
        
        for path in image_paths:
            try:
                image = Image.open(path).convert('RGB')
                images.append(image)
                valid_paths.append(path)
            except Exception as e:
                print(f"Error loading {path}: {e}")
                continue
        
        if not images:
            return None, []
            
        inputs = self.processor(images=images, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            image_features = F.normalize(image_features, p=2, dim=-1)
        
        return image_features, valid_paths
    
    def compute_similarities(self, text_features, image_features):
        """Compute cosine similarities between text and image embeddings"""
        similarities = torch.mm(image_features, text_features.t())
        return similarities.cpu().numpy()

def analyze_training_data():
    """Analyze training data with TinyCLIP embeddings"""
    
    # Initialize the comparator
    comparator = TinyCLIPComparator()
    
    # Text queries to test
    text_queries = ["first dates", "first dates logo"]
    
    # Get text embeddings
    print("Getting text embeddings...")
    text_features = comparator.get_text_embeddings(text_queries)
    
    # Data paths
    base_path = Path("data")
    train_path = base_path / "train"
    
    results = {
        "text_queries": text_queries,
        "results": {}
    }
    
    # Analyze each class
    for class_name in ["yes", "no"]:
        class_path = train_path / class_name
        if not class_path.exists():
            print(f"Warning: {class_path} does not exist")
            continue
            
        # Get all image files
        image_files = list(class_path.glob("*.png")) + list(class_path.glob("*.jpg"))
        image_paths = [str(path) for path in image_files]
        
        print(f"Processing {len(image_paths)} images from {class_name} class...")
        
        # Process images in batches to avoid memory issues
        batch_size = 32
        all_similarities = []
        all_image_names = []
        
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            
            # Get image embeddings
            image_features, valid_paths = comparator.get_image_embeddings(batch_paths)
            
            if image_features is None:
                continue
            
            # Compute similarities
            similarities = comparator.compute_similarities(text_features, image_features)
            
            # Store results
            for j, path in enumerate(valid_paths):
                image_name = Path(path).name
                all_similarities.append(similarities[j].tolist())
                all_image_names.append(image_name)
                
            print(f"  Processed batch {i//batch_size + 1}/{(len(image_paths) + batch_size - 1)//batch_size}")
        
        # Calculate statistics
        if all_similarities:
            similarities_array = np.array(all_similarities)
            
            class_results = {
                "num_images": len(all_similarities),
                "similarities": {
                    query: {
                        "mean": float(similarities_array[:, idx].mean()),
                        "std": float(similarities_array[:, idx].std()),
                        "min": float(similarities_array[:, idx].min()),
                        "max": float(similarities_array[:, idx].max()),
                        "median": float(np.median(similarities_array[:, idx]))
                    } for idx, query in enumerate(text_queries)
                },
                "top_matches": {}
            }
            
            # Find top matches for each query
            for idx, query in enumerate(text_queries):
                query_sims = similarities_array[:, idx]
                top_indices = np.argsort(query_sims)[::-1][:10]  # Top 10
                
                class_results["top_matches"][query] = [
                    {
                        "image": all_image_names[i],
                        "similarity": float(query_sims[i])
                    } for i in top_indices
                ]
            
            results["results"][class_name] = class_results
            
            print(f"\n{class_name.upper()} CLASS STATISTICS:")
            print(f"  Number of images: {len(all_similarities)}")
            for idx, query in enumerate(text_queries):
                stats = class_results["similarities"][query]
                print(f"  '{query}' similarities:")
                print(f"    Mean: {stats['mean']:.4f} ± {stats['std']:.4f}")
                print(f"    Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
                print(f"    Median: {stats['median']:.4f}")
                
    # Compare classes
    print("\n" + "="*60)
    print("COMPARISON BETWEEN CLASSES:")
    print("="*60)
    
    if "yes" in results["results"] and "no" in results["results"]:
        for query in text_queries:
            yes_mean = results["results"]["yes"]["similarities"][query]["mean"]
            no_mean = results["results"]["no"]["similarities"][query]["mean"]
            
            print(f"\n'{query}' query:")
            print(f"  YES class mean similarity: {yes_mean:.4f}")
            print(f"  NO class mean similarity:  {no_mean:.4f}")
            print(f"  Difference (YES - NO):     {yes_mean - no_mean:.4f}")
            
            if yes_mean > no_mean:
                print(f"  → YES class is more similar to '{query}'")
            else:
                print(f"  → NO class is more similar to '{query}'")
    
    # Save detailed results
    output_file = "tinyclip_analysis_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Show top matches
    print("\n" + "="*60)
    print("TOP MATCHES FOR EACH CLASS:")
    print("="*60)
    
    for class_name in ["yes", "no"]:
        if class_name in results["results"]:
            print(f"\n{class_name.upper()} CLASS:")
            for query in text_queries:
                print(f"  Top 5 matches for '{query}':")
                top_matches = results["results"][class_name]["top_matches"][query][:5]
                for i, match in enumerate(top_matches, 1):
                    print(f"    {i}. {match['image']} (sim: {match['similarity']:.4f})")

if __name__ == "__main__":
    print("TinyCLIP Analysis for Binary Classification")
    print("=" * 50)
    print("Analyzing embeddings for 'first dates' and 'first dates logo'")
    print("against YES/NO training data samples...\n")
    
    try:
        analyze_training_data()
        print("\nAnalysis completed successfully!")
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()