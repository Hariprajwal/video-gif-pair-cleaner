import os
import shutil
import re
from difflib import SequenceMatcher

def extract_core_name(name):
    """
    Extract the core name by removing common patterns, YouTube IDs, file extensions, etc.
    """
    # Remove file extensions
    name = re.sub(r'\.(mp4|avi|mkv|mov|wmv|flv|webm|m4v|3gp|mpeg|mpg|ts|mts|m2ts|vob|ogv|divx|xvid|gifs)$', '', name, flags=re.IGNORECASE)
    
    # Remove YouTube IDs in brackets
    name = re.sub(r'\[.*?\]', '', name)
    
    # Remove common video-related words that might differ
    common_terms = [
        'official', 'trailer', 'teaser', 'hd', 'full', 'movie', 'video',
        'download', '1080p', '720p', '4k', 'scene', 'clip', 'part',
        'version', 'extended', 'director', 'cut', 'subtitles', 'subs'
    ]
    
    # Remove these terms (case insensitive)
    pattern = r'\b(' + '|'.join(common_terms) + r')\b'
    name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # Remove extra spaces and special characters, keep only alphanumeric and spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name.lower()

def similarity_score(str1, str2):
    """Calculate similarity between two strings (0 to 1)"""
    return SequenceMatcher(None, str1, str2).ratio()

def find_best_video_match(folder_name, downloads_path, threshold=0.7):
    """
    Find the best matching video file using multiple strategies
    """
    folder_core = extract_core_name(folder_name)
    
    # Common video file extensions
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', 
                       '.webm', '.m4v', '.3gp', '.mpeg', '.mpg', '.ts',
                       '.mts', '.m2ts', '.vob', '.ogv', '.divx', '.xvid']
    
    best_match = None
    best_score = 0
    
    for filename in os.listdir(downloads_path):
        if not any(filename.lower().endswith(ext) for ext in video_extensions):
            continue
            
        video_core = extract_core_name(filename)
        
        # Strategy 1: Direct core comparison
        score1 = similarity_score(folder_core, video_core)
        
        # Strategy 2: Check if folder core is contained in video core or vice versa
        contains_score = 0
        if folder_core in video_core or video_core in folder_core:
            contains_score = 0.8  # Boost score for containment
        
        # Strategy 3: Word overlap
        folder_words = set(folder_core.split())
        video_words = set(video_core.split())
        if folder_words and video_words:
            word_overlap = len(folder_words.intersection(video_words)) / len(folder_words.union(video_words))
        else:
            word_overlap = 0
        
        # Combined score (weighted)
        total_score = (score1 * 0.5) + (contains_score * 0.3) + (word_overlap * 0.2)
        
        if total_score > best_score and total_score >= threshold:
            best_score = total_score
            best_match = os.path.join(downloads_path, filename)
    
    return best_match, best_score

def find_videos_by_content_similarity(folder_name, downloads_path):
    """
    Alternative approach: Look for videos that have high content similarity
    """
    # Remove .gifs extension for base comparison
    folder_base = folder_name.replace('.gifs', '')
    
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', 
                       '.webm', '.m4v', '.3gp', '.mpeg', '.mpg', '.ts',
                       '.mts', '.m2ts', '.vob', '.ogv', '.divx', '.xvid']
    
    potential_matches = []
    
    for filename in os.listdir(downloads_path):
        if not any(filename.lower().endswith(ext) for ext in video_extensions):
            continue
            
        video_base = os.path.splitext(filename)[0]
        
        # Multiple comparison strategies
        
        # 1. Direct similarity after basic cleaning
        clean_folder = re.sub(r'[^\w\s]', ' ', folder_base).lower()
        clean_video = re.sub(r'\[.*?\]', '', video_base)  # Remove YouTube ID first
        clean_video = re.sub(r'[^\w\s]', ' ', clean_video).lower()
        
        clean_folder = re.sub(r'\s+', ' ', clean_folder).strip()
        clean_video = re.sub(r'\s+', ' ', clean_video).strip()
        
        similarity = SequenceMatcher(None, clean_folder, clean_video).ratio()
        
        # 2. Check if one is essentially the spaced version of the other
        folder_no_spaces = re.sub(r'\s+', '', clean_folder)
        video_no_spaces = re.sub(r'\s+', '', clean_video)
        
        no_space_similarity = SequenceMatcher(None, folder_no_spaces, video_no_spaces).ratio()
        
        # 3. Word-based similarity
        folder_words = set(clean_folder.split())
        video_words = set(clean_video.split())
        
        if folder_words and video_words:
            common_words = folder_words.intersection(video_words)
            word_similarity = len(common_words) / max(len(folder_words), len(video_words))
        else:
            word_similarity = 0
        
        # Combined score
        combined_score = max(similarity, no_space_similarity, word_similarity)
        
        if combined_score > 0.6:  # Lower threshold for this method
            potential_matches.append({
                'path': os.path.join(downloads_path, filename),
                'filename': filename,
                'score': combined_score,
                'clean_folder': clean_folder,
                'clean_video': clean_video
            })
    
    if potential_matches:
        # Return the best match
        best_match = max(potential_matches, key=lambda x: x['score'])
        return best_match['path'], best_match['score']
    
    return None, 0

def debug_matching(folder_name, downloads_path):
    """
    Debug function to see what matching attempts are being made
    """
    print(f"\n🔍 DEBUG: Matching for folder: {folder_name}")
    
    folder_core = extract_core_name(folder_name)
    print(f"   Core name: '{folder_core}'")
    
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
    
    for filename in os.listdir(downloads_path):
        if not any(filename.lower().endswith(ext) for ext in video_extensions):
            continue
            
        video_core = extract_core_name(filename)
        score = similarity_score(folder_core, video_core)
        
        if score > 0.3:  # Show even weak matches for debugging
            print(f"   Potential: '{video_core}' -> score: {score:.2f}")
    
    best_match, best_score = find_best_video_match(folder_name, downloads_path, threshold=0.1)
    if best_match:
        print(f"   BEST MATCH: {os.path.basename(best_match)} -> score: {best_score:.2f}")
    else:
        print(f"   NO GOOD MATCH FOUND")

def cleanup_gifs_folders_and_videos():
    target_directory = r"C:\Users\harip\ALL TEST"
    downloads_directory = r"D:\downloads"
    
    if not os.path.exists(target_directory):
        print(f"❌ Directory not found: {target_directory}")
        return 0, 0
    
    if not os.path.exists(downloads_directory):
        print(f"❌ Downloads directory not found: {downloads_directory}")
        return 0, 0
    
    try:
        # Get all items in the directory
        all_items = os.listdir(target_directory)
        
        # Filter only folders that end with .gifs
        gifs_folders = []
        for item in all_items:
            item_path = os.path.join(target_directory, item)
            if os.path.isdir(item_path) and item.endswith('.gifs'):
                gifs_folders.append(item)
        
        # Find pairs where both .gifs folder AND corresponding video file exist
        deletion_pairs = []
        
        for folder in gifs_folders:
            # Try the main matching algorithm first
            video_file, score = find_best_video_match(folder, downloads_directory, threshold=0.65)
            
            # If no good match found, try the alternative method
            if not video_file:
                video_file, score = find_videos_by_content_similarity(folder, downloads_directory)
            
            if video_file and os.path.exists(video_file):
                deletion_pairs.append({
                    'folder': folder,
                    'folder_path': os.path.join(target_directory, folder),
                    'video_file': video_file,
                    'video_name': os.path.basename(video_file),
                    'similarity_score': score
                })
        
        # Count results
        pair_count = len(deletion_pairs)
        
        if pair_count == 0:
            print("❌ No matching pairs found with current thresholds.")
            print("💡 Running debug mode to see matching attempts...")
            for folder in gifs_folders[:3]:  # Show first 3 for debugging
                debug_matching(folder, downloads_directory)
            return 0, 0
        
        print(f"📁 Found {pair_count} .gifs folder + video file pair(s) (BOTH exist):")
        for i, pair in enumerate(deletion_pairs, 1):
            print(f"  {i}. {pair['folder']}")
            print(f"     └──▶ {pair['video_name']} (score: {pair['similarity_score']:.2f})")
        
        # Ask for confirmation before deletion
        print(f"\n⚠️  WARNING: This will permanently delete {pair_count} pairs:")
        print(f"   - .gifs folders from {target_directory}")
        print(f"   - Corresponding video files from {downloads_directory}")
        print("   This action cannot be undone!")
        
        confirmation = input("\nType 'YES' to confirm deletion, or anything else to cancel: ").strip()
        
        if confirmation.upper() == 'YES':
            deleted_folder_count = 0
            deleted_video_count = 0
            
            # Delete both folders and videos
            for pair in deletion_pairs:
                # Delete .gifs folder
                try:
                    shutil.rmtree(pair['folder_path'])
                    print(f"✅ Deleted folder: {pair['folder']}")
                    deleted_folder_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete folder {pair['folder']}: {e}")
                    continue
                
                # Delete video file
                try:
                    os.remove(pair['video_file'])
                    print(f"✅ Deleted video: {pair['video_name']}")
                    deleted_video_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete video {pair['video_name']}: {e}")
            
            print(f"\n🎉 Cleanup completed!")
            print(f"   - Deleted {deleted_folder_count} .gifs folder(s)")
            print(f"   - Deleted {deleted_video_count} video file(s)")
            
            return deleted_folder_count, deleted_video_count
        else:
            print("❌ Deletion cancelled by user.")
            return 0, 0
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return 0, 0

def preview_cleanup():
    """
    Preview what would be deleted without actually deleting anything
    """
    target_directory = r"C:\Users\harip\ALL TEST"
    downloads_directory = r"D:\downloads"
    
    print("\n🔍 PREVIEW MODE (No files will be deleted)")
    print("=" * 50)
    
    if not os.path.exists(target_directory):
        print(f"❌ Directory not found: {target_directory}")
        return
    
    if not os.path.exists(downloads_directory):
        print(f"❌ Downloads directory not found: {downloads_directory}")
        return
    
    try:
        # Get all items in the directory
        all_items = os.listdir(target_directory)
        
        # Filter only folders that end with .gifs
        gifs_folders = []
        for item in all_items:
            item_path = os.path.join(target_directory, item)
            if os.path.isdir(item_path) and item.endswith('.gifs'):
                gifs_folders.append(item)
        
        # Find pairs where both exist
        deletion_pairs = []
        folders_without_videos = []
        
        for folder in gifs_folders:
            video_file, score = find_best_video_match(folder, downloads_directory, threshold=0.65)
            
            if not video_file:
                video_file, score = find_videos_by_content_similarity(folder, downloads_directory)
            
            if video_file and os.path.exists(video_file):
                deletion_pairs.append({
                    'folder': folder,
                    'video_name': os.path.basename(video_file),
                    'score': score
                })
            else:
                folders_without_videos.append(folder)
        
        # Display results
        if deletion_pairs:
            print(f"\n🎯 WOULD BE DELETED ({len(deletion_pairs)} pairs - BOTH exist):")
            for i, pair in enumerate(deletion_pairs, 1):
                print(f"  {i}. {pair['folder']}")
                print(f"     └──▶ {pair['video_name']} (score: {pair['score']:.2f})")
        else:
            print(f"\n❌ No .gifs folder + video file pairs found with current thresholds")
            print("💡 Try lowering the similarity threshold or check the debug output")
        
        if folders_without_videos:
            print(f"\n📁 FOLDERS WITHOUT MATCHING VIDEOS ({len(folders_without_videos)} - would NOT be deleted):")
            for i, folder in enumerate(folders_without_videos, 1):
                print(f"  {i}. {folder}")
        
        print(f"\n💡 Only pairs where BOTH .gifs folder AND matching video file exist will be deleted!")
        
    except Exception as e:
        print(f"❌ Error during preview: {e}")

# --- Main Program Execution ---
if __name__ == "__main__":
    
    print("🧹 .GIFS FOLDER & VIDEO CLEANUP TOOL")
    print("=" * 50)
    print("💡 Advanced matching with multiple algorithms!")
    print("💡 Only deletes when BOTH .gifs folder AND matching video file exist!")
    
    # Ask if user wants to preview first
    preview = input("\n🔍 Do you want to preview what would be deleted first? (y/n): ").strip().lower()
    if preview == 'y' or preview == 'yes':
        preview_cleanup()
        print("\n" + "="*50)
    
    # Run the cleanup function
    deleted_folders, deleted_videos = cleanup_gifs_folders_and_videos()
    
    print(f"\n{'='*50}")
    print("📊 CLEANUP SUMMARY")
    print(f"{'='*50}")
    print(f"🗑️  Folders deleted: {deleted_folders}")
    print(f"🎬 Videos deleted: {deleted_videos}")
    print("🎉 Operation completed!")
