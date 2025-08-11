import torch
import torch.nn.functional as F
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import os
import numpy as np
import json
from pathlib import Path
import time

class TinyCLIPFullTrainingSet:
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
        
    def analyze_full_training_set(self, batch_size=16):
        """
        Analyze the entire training set with bottom-left cropping
        """
        
        # Text queries to test
        text_queries = ["first dates", "first dates logo", "first DATES", "first DATES logo"]
        
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
        overall_stats = {}
        
        # Analyze each class
        for class_name in ["yes", "no"]:
            class_path = train_path / class_name
            if not class_path.exists():
                print(f"Warning: {class_path} does not exist")
                continue
                
            # Get all image files
            image_files = list(class_path.glob("*.png")) + list(class_path.glob("*.jpg"))
            print(f"\nProcessing {len(image_files)} images from {class_name} class...")
            
            # Process images in batches to manage memory
            all_similarities = []
            all_image_names = []
            failed_images = 0
            processed_batches = 0
            
            start_time = time.time()
            
            for i in range(0, len(image_files), batch_size):
                batch_paths = image_files[i:i + batch_size]
                
                # Load and process images for this batch
                batch_images = []
                batch_names = []
                
                for img_path in batch_paths:
                    try:
                        # Load and crop to bottom-left
                        image = Image.open(img_path).convert('RGB')
                        cropped_image = self.crop_bottom_left(image)
                        
                        batch_images.append(cropped_image)
                        batch_names.append(img_path.name)
                    except Exception as e:
                        print(f"    Error loading {img_path.name}: {e}")
                        failed_images += 1
                        continue
                
                if not batch_images:
                    continue
                
                # Get image embeddings for this batch
                inputs = self.processor(images=batch_images, return_tensors="pt", padding=True)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    image_features = self.model.get_image_features(**inputs)
                    image_features = F.normalize(image_features, p=2, dim=-1)
                
                # Compute similarities
                similarities = torch.mm(image_features, text_features.t())
                similarities = similarities.cpu().numpy()
                
                # Store results
                all_similarities.extend(similarities.tolist())
                all_image_names.extend(batch_names)
                
                processed_batches += 1
                
                # Progress update every 10 batches
                if processed_batches % 10 == 0:
                    elapsed = time.time() - start_time
                    progress = (i + batch_size) / len(image_files) * 100
                    print(f"    Progress: {progress:.1f}% ({processed_batches} batches, {elapsed:.1f}s)")
            
            if not all_similarities:
                print(f"    No valid images processed for {class_name} class!")
                continue
                
            # Convert to numpy array for analysis
            similarities_array = np.array(all_similarities)
            
            # Calculate comprehensive statistics
            class_results = {
                "total_images": len(image_files),
                "processed_images": len(all_similarities),
                "failed_images": failed_images,
                "processing_time": time.time() - start_time,
                "queries": {}
            }
            
            for idx, query in enumerate(text_queries):
                query_sims = similarities_array[:, idx]
                
                # Calculate detailed statistics
                sorted_sims = np.sort(query_sims)
                
                query_stats = {
                    "mean": float(query_sims.mean()),
                    "std": float(query_sims.std()),
                    "min": float(query_sims.min()),
                    "max": float(query_sims.max()),
                    "median": float(np.median(query_sims)),
                    "q25": float(np.percentile(query_sims, 25)),
                    "q75": float(np.percentile(query_sims, 75)),
                    "iqr": float(np.percentile(query_sims, 75) - np.percentile(query_sims, 25))
                }
                
                # Find top and bottom matches
                top_indices = np.argsort(query_sims)[::-1][:10]  # Top 10
                bottom_indices = np.argsort(query_sims)[:10]      # Bottom 10
                
                query_stats["top_matches"] = [
                    {"image": all_image_names[i], "similarity": float(query_sims[i])}
                    for i in top_indices
                ]
                
                query_stats["bottom_matches"] = [
                    {"image": all_image_names[i], "similarity": float(query_sims[i])}
                    for i in bottom_indices
                ]
                
                class_results["queries"][query] = query_stats
            
            results[class_name] = class_results
            
            # Print class summary
            total_time = time.time() - start_time
            print(f"    Completed: {class_results['processed_images']}/{class_results['total_images']} images")
            print(f"    Failed: {failed_images} images")
            print(f"    Time: {total_time:.1f}s ({total_time/class_results['processed_images']:.3f}s per image)")
        
        return results, text_queries

def main():
    print("TinyCLIP Full Training Set Analysis")
    print("=" * 60)
    print("Processing ENTIRE training set with bottom-left cropping")
    print("This may take several minutes depending on dataset size...")
    print()
    
    try:
        analyzer = TinyCLIPFullTrainingSet()
        results, text_queries = analyzer.analyze_full_training_set(batch_size=16)
        
        # Display comprehensive results
        print("\n" + "="*80)
        print("COMPLETE TRAINING SET RESULTS")
        print("="*80)
        
        total_processed = 0
        total_images = 0
        
        for class_name in ["yes", "no"]:
            if class_name in results:
                class_data = results[class_name]
                total_processed += class_data["processed_images"]
                total_images += class_data["total_images"]
                
                print(f"\n{class_name.upper()} CLASS SUMMARY:")
                print(f"  Total images: {class_data['total_images']}")
                print(f"  Successfully processed: {class_data['processed_images']}")
                print(f"  Failed: {class_data['failed_images']}")
                print(f"  Processing time: {class_data['processing_time']:.1f}s")
                
                for query in text_queries:
                    if query in class_data["queries"]:
                        stats = class_data["queries"][query]
                        print(f"\n  '{query}' similarities:")
                        print(f"    Mean: {stats['mean']:.4f} ± {stats['std']:.4f}")
                        print(f"    Median: {stats['median']:.4f}")
                        print(f"    Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
                        print(f"    IQR: {stats['q25']:.4f} to {stats['q75']:.4f} (width: {stats['iqr']:.4f})")
                        
                        print(f"    Top 3 matches:")
                        for i, match in enumerate(stats["top_matches"][:3], 1):
                            print(f"      {i}. {match['image']} (sim: {match['similarity']:.4f})")
        
        # Overall comparison
        print("\n" + "="*80)
        print("COMPREHENSIVE CLASS COMPARISON")
        print("="*80)
        
        print(f"Total dataset: {total_images} images ({total_processed} processed successfully)")
        print()
        
        if "yes" in results and "no" in results:
            for query in text_queries:
                if query in results["yes"]["queries"] and query in results["no"]["queries"]:
                    yes_stats = results["yes"]["queries"][query]
                    no_stats = results["no"]["queries"][query]
                    
                    print(f"Query: '{query}'")
                    print("-" * 50)
                    print(f"  NO class:  mean={no_stats['mean']:.4f}, std={no_stats['std']:.4f}, median={no_stats['median']:.4f}")
                    print(f"  YES class: mean={yes_stats['mean']:.4f}, std={yes_stats['std']:.4f}, median={yes_stats['median']:.4f}")
                    
                    mean_diff = no_stats['mean'] - yes_stats['mean']
                    median_diff = no_stats['median'] - yes_stats['median']
                    
                    print(f"  Mean difference (NO-YES): {mean_diff:+.4f}")
                    print(f"  Median difference (NO-YES): {median_diff:+.4f}")
                    
                    if mean_diff > 0:
                        print(f"  -> NO class is MORE similar to '{query}' (CORRECT)")
                        
                        # Calculate effect size (Cohen's d)
                        pooled_std = np.sqrt((yes_stats['std']**2 + no_stats['std']**2) / 2)
                        cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0
                        print(f"  -> Effect size (Cohen's d): {cohens_d:.3f}")
                        
                        if cohens_d > 0.8:
                            print("     (Large effect - very good separation)")
                        elif cohens_d > 0.5:
                            print("     (Medium effect - good separation)")
                        elif cohens_d > 0.2:
                            print("     (Small effect - some separation)")
                        else:
                            print("     (Negligible effect)")
                    else:
                        print(f"  -> YES class is MORE similar to '{query}' (unexpected)")
                    print()
        
        # Save comprehensive results
        output_file = "tinyclip_full_training_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Complete results saved to: {output_file}")
        
        # Classification potential assessment
        print("\n" + "="*80)
        print("CLASSIFICATION POTENTIAL ASSESSMENT")
        print("="*80)
        
        if "yes" in results and "no" in results:
            for query in text_queries:
                if query in results["yes"]["queries"] and query in results["no"]["queries"]:
                    yes_stats = results["yes"]["queries"][query]
                    no_stats = results["no"]["queries"][query]
                    
                    # Calculate separation metrics
                    mean_separation = abs(no_stats['mean'] - yes_stats['mean'])
                    overlap_estimate = max(0, min(yes_stats['max'], no_stats['max']) - max(yes_stats['min'], no_stats['min']))
                    range_yes = yes_stats['max'] - yes_stats['min']
                    range_no = no_stats['max'] - no_stats['min']
                    total_range = max(yes_stats['max'], no_stats['max']) - min(yes_stats['min'], no_stats['min'])
                    
                    separation_ratio = mean_separation / total_range if total_range > 0 else 0
                    
                    print(f"'{query}' as classifier:")
                    print(f"  Mean separation: {mean_separation:.4f}")
                    print(f"  Separation ratio: {separation_ratio:.3f}")
                    
                    if separation_ratio > 0.3:
                        print("  -> EXCELLENT classification potential")
                    elif separation_ratio > 0.2:
                        print("  -> GOOD classification potential") 
                    elif separation_ratio > 0.1:
                        print("  -> MODERATE classification potential")
                    else:
                        print("  -> LIMITED classification potential")
                    print()
        
        print("\nFull training set analysis completed successfully!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()