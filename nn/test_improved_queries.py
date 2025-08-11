import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import os
import numpy as np
import json
from pathlib import Path

class ImprovedQueryTester:
    def __init__(self):
        print("Loading CLIP model...")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        print(f"Model loaded on {self.device}")
        
    def crop_bottom_left(self, image):
        """Crop the bottom-left corner of the image"""
        width, height = image.size
        grid_width = width // 5
        grid_height = height // 4
        
        left = 0
        top = height - grid_height
        right = grid_width
        bottom = height
        
        cropped = image.crop((left, top, right, bottom))
        return cropped
        
    def test_new_queries(self, sample_size=100):
        """
        Test new queries based on visual analysis of the bottom-left crop
        """
        
        # Original best queries for comparison
        baseline_queries = ["first dates", "first dates logo"]
        
        # New queries based on visual analysis of the cropped region
        new_queries = [
            # Specific to what we see in the crop
            "first DATES white text",
            "white text on dark background", 
            "TV show title",
            "dating show logo",
            
            # More general but potentially better
            "reality TV show",
            "German TV show",
            "dating program",
            "television branding",
            
            # Typography-focused  
            "white typography",
            "show title text",
            
            # Very specific combinations
            "first DATES TV show",
            "dating reality show"
        ]
        
        # Combine all queries
        all_queries = baseline_queries + new_queries
        
        print(f"Testing {len(all_queries)} different queries:")
        for i, query in enumerate(all_queries, 1):
            marker = "(BASELINE)" if query in baseline_queries else "(NEW)"
            print(f"  {i:2d}. '{query}' {marker}")
        print()
        
        # Get text embeddings
        print("Getting text embeddings...")
        inputs = self.processor(text=all_queries, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = F.normalize(text_features, p=2, dim=-1)
        
        # Data paths
        base_path = Path("data")
        train_path = base_path / "train"
        
        results = {}
        
        # Sample images from each class
        for class_name in ["yes", "no"]:
            class_path = train_path / class_name
            if not class_path.exists():
                continue
                
            image_files = list(class_path.glob("*.png")) + list(class_path.glob("*.jpg"))
            
            # Sample for faster testing
            if len(image_files) > sample_size:
                import random
                image_files = random.sample(image_files, sample_size)
            
            print(f"Processing {len(image_files)} sample images from {class_name} class...")
            
            # Load and process images
            images = []
            for img_path in image_files:
                try:
                    image = Image.open(img_path).convert('RGB')
                    cropped_image = self.crop_bottom_left(image)
                    images.append(cropped_image)
                except Exception as e:
                    print(f"  Error loading {img_path}: {e}")
                    continue
            
            if not images:
                continue
                
            # Process in batches
            batch_size = 16
            all_similarities = []
            
            for i in range(0, len(images), batch_size):
                batch_images = images[i:i + batch_size]
                
                inputs = self.processor(images=batch_images, return_tensors="pt", padding=True)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    image_features = self.model.get_image_features(**inputs)
                    image_features = F.normalize(image_features, p=2, dim=-1)
                
                similarities = torch.mm(image_features, text_features.t())
                all_similarities.extend(similarities.cpu().numpy().tolist())
            
            # Calculate statistics for each query
            similarities_array = np.array(all_similarities)
            
            class_results = {}
            for idx, query in enumerate(all_queries):
                query_sims = similarities_array[:, idx]
                
                class_results[query] = {
                    "mean": float(query_sims.mean()),
                    "std": float(query_sims.std()),
                    "median": float(np.median(query_sims)),
                    "max": float(query_sims.max())
                }
            
            results[class_name] = {
                "num_samples": len(all_similarities),
                "queries": class_results
            }
            
            print(f"  Completed {class_name} class")
        
        return results, all_queries, baseline_queries, new_queries

def main():
    print("Testing Improved Text Queries")
    print("=" * 50)
    print("Based on visual analysis of the bottom-left crop showing:")
    print("- Clear 'first DATES' white text logo")
    print("- Dark reddish background")
    print("- Professional TV show branding")
    print()
    
    try:
        tester = ImprovedQueryTester()
        results, all_queries, baseline_queries, new_queries = tester.test_new_queries(sample_size=100)
        
        # Find the best performing queries
        if "yes" in results and "no" in results:
            query_performance = {}
            
            for query in all_queries:
                if query in results["yes"]["queries"] and query in results["no"]["queries"]:
                    yes_mean = results["yes"]["queries"][query]["mean"]
                    no_mean = results["no"]["queries"][query]["mean"]
                    
                    # We want NO class to have higher similarity (correct for "first dates" content)
                    difference = no_mean - yes_mean
                    separation = abs(difference)
                    
                    query_performance[query] = {
                        "no_mean": no_mean,
                        "yes_mean": yes_mean,
                        "difference": difference,
                        "separation": separation,
                        "correct_direction": difference > 0
                    }
            
            # Sort by separation (best separation first)
            sorted_queries = sorted(query_performance.items(), 
                                  key=lambda x: x[1]["separation"], 
                                  reverse=True)
            
            print("\n" + "="*80)
            print("QUERY PERFORMANCE RANKING (by class separation)")
            print("="*80)
            print("Rank | Query | NO Mean | YES Mean | Difference | Direction")
            print("-" * 80)
            
            for rank, (query, stats) in enumerate(sorted_queries[:15], 1):
                direction = "CORRECT" if stats["correct_direction"] else "WRONG"
                baseline_marker = " (BASELINE)" if query in baseline_queries else ""
                
                print(f"{rank:2d}   | {query:<25} | {stats['no_mean']:.4f}  | {stats['yes_mean']:.4f}  | "
                      f"{stats['difference']:+.4f}   | {direction}{baseline_marker}")
            
            # Highlight top new queries
            print("\n" + "="*80)
            print("TOP NEW QUERY DISCOVERIES:")
            print("="*80)
            
            new_query_performance = [(q, s) for q, s in sorted_queries if q not in baseline_queries]
            
            for rank, (query, stats) in enumerate(new_query_performance[:5], 1):
                improvement = "IMPROVEMENT" if stats["separation"] > 0.15 else "SIMILAR"
                print(f"{rank}. '{query}'")
                print(f"   Separation: {stats['separation']:.4f} | {improvement}")
                print(f"   NO: {stats['no_mean']:.4f} | YES: {stats['yes_mean']:.4f}")
                print()
            
            # Compare to baseline
            print("COMPARISON TO BASELINE:")
            print("-" * 40)
            
            baseline_best = max([(q, s) for q, s in sorted_queries if q in baseline_queries], 
                              key=lambda x: x[1]["separation"])
            new_best = max(new_query_performance, key=lambda x: x[1]["separation"])
            
            print(f"Best baseline: '{baseline_best[0]}' (separation: {baseline_best[1]['separation']:.4f})")
            print(f"Best new query: '{new_best[0]}' (separation: {new_best[1]['separation']:.4f})")
            
            improvement_pct = ((new_best[1]["separation"] - baseline_best[1]["separation"]) / 
                             baseline_best[1]["separation"] * 100)
            
            if improvement_pct > 0:
                print(f"IMPROVEMENT: +{improvement_pct:.1f}% better separation!")
            else:
                print(f"No significant improvement over baseline ({improvement_pct:.1f}%)")
        
        # Save results
        output_file = "improved_queries_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "results": results,
                "all_queries": all_queries,
                "baseline_queries": baseline_queries,
                "new_queries": new_queries
            }, f, indent=2)
        print(f"\nDetailed results saved to: {output_file}")
        
        print("\nImproved query testing completed!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()