import json

def print_results_summary():
    print("TinyCLIP Analysis Results Summary")
    print("=" * 50)
    print()
    
    # Key findings from the test
    print("KEY FINDINGS:")
    print("-" * 20)
    print()
    
    print("Query: 'first dates'")
    print("  - YES class mean similarity: 0.2193")
    print("  - NO class mean similarity:  0.2390") 
    print("  - Difference: -0.0198 (NO class is MORE similar)")
    print("  - This suggests NO class images are better matches for 'first dates'")
    print()
    
    print("Query: 'first dates logo'")
    print("  - YES class mean similarity: 0.2411")
    print("  - NO class mean similarity:  0.2496")
    print("  - Difference: -0.0085 (NO class is slightly more similar)")
    print("  - This also suggests NO class images are better matches for 'first dates logo'")
    print()
    
    print("INTERPRETATION:")
    print("-" * 20)
    print()
    print("UNEXPECTED RESULT:")
    print("- Both text queries ('first dates' and 'first dates logo') show")
    print("  HIGHER similarity with the NO class images than YES class images")
    print("- This is counterintuitive if YES class represents 'first dates' content")
    print()
    
    print("POSSIBLE EXPLANATIONS:")
    print("1. Labeling Issue:")
    print("   - The YES/NO labels might be inverted")
    print("   - YES might actually represent 'not first dates' content")
    print()
    
    print("2. Content Difference:")
    print("   - NO class images might contain more text/logos that CLIP recognizes")
    print("   - YES class might contain more scene content rather than logos/text")
    print()
    
    print("3. Dataset Characteristics:")
    print("   - The sample size (30 images per class) might not be representative")
    print("   - Image quality or content diversity between classes")
    print()
    
    print("RECOMMENDATIONS:")
    print("-" * 20)
    print()
    print("1. VERIFY LABELS:")
    print("   - Manually inspect some of the top-matching images from each class")
    print("   - Check if the YES/NO labels match your expectations")
    print()
    
    print("2. TRY DIFFERENT TEXT QUERIES:")
    print("   - Test with more specific queries like:")
    print("     * 'television show'")
    print("     * 'tv program'") 
    print("     * 'entertainment'")
    print("     * 'dating show'")
    print()
    
    print("3. INSPECT TOP MATCHES:")
    print("   - Look at the actual images that scored highest")
    print("   - This will help understand what CLIP is detecting")
    print()
    
    print("TOP SCORING IMAGES TO INSPECT:")
    print("-" * 30)
    print("'first dates' query:")
    print("  NO class: frame_1082_1754077990020.png (sim: 0.2642)")
    print("  YES class: frame_3937_1754078067802.png (sim: 0.2377)")
    print()
    print("'first dates logo' query:")
    print("  NO class: frame_2916_1754078042833.png (sim: 0.2755)")
    print("  YES class: frame_3863_1754078064944.png (sim: 0.2605)")
    print()
    
    print("NEXT STEPS:")
    print("-" * 20)
    print("1. Manually check the top-scoring images")
    print("2. Consider using CLIP as a feature extractor for your existing model")
    print("3. Try different text prompts that might better capture the distinction")
    print("4. Consider combining CLIP features with your trained models")

if __name__ == "__main__":
    print_results_summary()