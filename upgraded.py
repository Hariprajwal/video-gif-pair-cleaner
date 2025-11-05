#!/usr/bin/env python3
"""
clean_pairs.py

Scans a target directory for folders ending with ".gifs" and tries to find matching video files
in a downloads directory. If BOTH a .gifs folder and a matching video file are found, the pair
is deleted (or moved to trash when send2trash is available).

Usage:
    python clean_pairs.py --target "C:\Users\harip\ALL TEST" --downloads "D:\downloads" --dry-run
"""

from __future__ import annotations
import os
import re
import argparse
import shutil
import logging
from difflib import SequenceMatcher
from typing import Optional, Tuple, List, Dict

# Try to import send2trash for safe deletion (moves to Recycle Bin/Trash).
try:
    from send2trash import send2trash  # type: ignore
    SEND_TO_TRASH_AVAILABLE = True
except Exception:
    SEND_TO_TRASH_AVAILABLE = False

# ---------------------------
# Utility / Matching Helpers
# ---------------------------
VIDEO_EXTS = [
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
    '.webm', '.m4v', '.3gp', '.mpeg', '.mpg', '.ts',
    '.mts', '.m2ts', '.vob', '.ogv', '.divx', '.xvid'
]

def extract_core_name(name: str) -> str:
    """
    Extract a simplified core name for matching:
    - Remove known extensions
    - Remove bracketed ids like [ABC123]
    - Remove common junk terms (hd, trailer, 1080p, etc.)
    - Keep only alphanumeric and spaces, collapse whitespace
    - Return lowercase
    """
    if not isinstance(name, str):
        return ''
    # Remove known file extensions (single gif, video extensions). IMPORTANT: 'gif' not 'gifs'
    name = re.sub(r'\.(mp4|avi|mkv|mov|wmv|flv|webm|m4v|3gp|mpeg|mpg|ts|mts|m2ts|vob|ogv|divx|xvid|gif)$',
                  '', name, flags=re.IGNORECASE)

    # Remove bracketed IDs like [abcd], (abcd)
    name = re.sub(r'[\[\(].*?[\]\)]', ' ', name)

    # Remove common terms that add noise
    common_terms = [
        'official', 'trailer', 'teaser', 'hd', 'full', 'movie', 'video',
        'download', '1080p', '720p', '4k', 'scene', 'clip', 'part',
        'version', 'extended', 'director', 'cut', 'subtitles', 'subs',
        'x264', 'h264', 'hevc', 'remux', 'bluray', 'bdrip'
    ]
    pattern = r'\b(' + '|'.join(common_terms) + r')\b'
    name = re.sub(pattern, ' ', name, flags=re.IGNORECASE)

    # Remove non-alphanumeric (keep spaces)
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    return name.lower()

def similarity_score(a: str, b: str) -> float:
    """Normalized ratio between 0 and 1 using SequenceMatcher"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

# ---------------------------
# Indexing helpers
# ---------------------------
def index_videos(downloads_path: str) -> Dict[str, str]:
    """
    Build a map {lower_filename: absolute_path} for all video files in downloads_path.
    Also returns a simple list of base names (no extension) for quick checks.
    """
    index = {}
    try:
        for entry in os.listdir(downloads_path):
            full = os.path.join(downloads_path, entry)
            if os.path.isfile(full) and any(entry.lower().endswith(ext) for ext in VIDEO_EXTS):
                index[entry] = full
    except Exception as exc:
        logging.error("Failed to list downloads directory %s: %s", downloads_path, exc)
    return index

# ---------------------------
# Matching algorithms
# ---------------------------
def find_best_video_match(folder_name: str, video_index: Dict[str, str], threshold: float = 0.7) -> Tuple[Optional[str], float]:
    """Try to find best video path from the video_index for folder_name."""
    folder_core = extract_core_name(folder_name)
    best_match = None
    best_score = 0.0

    for filename, full_path in video_index.items():
        video_core = extract_core_name(filename)
        # Strategy 1: Direct similarity
        score1 = similarity_score(folder_core, video_core)

        # Strategy 2: containment boost
        contains_score = 0.0
        if folder_core and video_core:
            if folder_core in video_core or video_core in folder_core:
                contains_score = 0.8

        # Strategy 3: word overlap
        folder_words = set(folder_core.split())
        video_words = set(video_core.split())
        word_overlap = 0.0
        if folder_words and video_words:
            word_overlap = len(folder_words.intersection(video_words)) / len(folder_words.union(video_words))

        total = (score1 * 0.5) + (contains_score * 0.3) + (word_overlap * 0.2)
        if total > best_score and total >= threshold:
            best_score = total
            best_match = full_path

    return best_match, best_score

def find_videos_by_content_similarity(folder_name: str, video_index: Dict[str, str], low_threshold: float = 0.6) -> Tuple[Optional[str], float]:
    """Alternative matching (no-space, basic cleaning). Returns best candidate if above low_threshold."""
    folder_base = folder_name.replace('.gifs', '')
    # basic cleaning
    clean_folder = re.sub(r'[^\w\s]', ' ', folder_base).lower()
    clean_folder = re.sub(r'\s+', ' ', clean_folder).strip()

    candidates = []
    for filename, full_path in video_index.items():
        video_base = os.path.splitext(filename)[0]
        clean_video = re.sub(r'[\[\(].*?[\]\)]', ' ', video_base)
        clean_video = re.sub(r'[^\w\s]', ' ', clean_video).lower()
        clean_video = re.sub(r'\s+', ' ', clean_video).strip()

        sim_direct = similarity_score(clean_folder, clean_video)
        sim_no_space = similarity_score(re.sub(r'\s+', '', clean_folder), re.sub(r'\s+', '', clean_video))
        folder_words = set(clean_folder.split())
        video_words = set(clean_video.split())
        word_similarity = 0.0
        if folder_words and video_words:
            common = folder_words.intersection(video_words)
            word_similarity = len(common) / max(len(folder_words), len(video_words))

        combined = max(sim_direct, sim_no_space, word_similarity)
        if combined >= low_threshold:
            candidates.append((combined, full_path))

    if not candidates:
        return None, 0.0
    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates[0][1], candidates[0][0]

# ---------------------------
# Main logic: find pairs and delete
# ---------------------------
def gather_pairs(target_directory: str, downloads_directory: str, threshold: float) -> List[Dict]:
    """
    Return a list of dicts:
    { 'folder': name, 'folder_path': ..., 'video_file': ..., 'video_name': ..., 'score': ... }
    """
    pairs = []
    video_index = index_videos(downloads_directory)
    if not os.path.isdir(target_directory):
        logging.warning("Target directory does not exist: %s", target_directory)
        return pairs

    try:
        for item in os.listdir(target_directory):
            item_path = os.path.join(target_directory, item)
            # Only directories that end with .gifs
            if os.path.isdir(item_path) and item.lower().endswith('.gifs'):
                # Try primary method
                video_file, score = find_best_video_match(item, video_index, threshold=threshold)
                # fallback
                if not video_file:
                    video_file, score = find_videos_by_content_similarity(item, video_index, low_threshold=threshold - 0.05)
                if video_file and os.path.exists(video_file):
                    pairs.append({
                        'folder': item,
                        'folder_path': item_path,
                        'video_file': video_file,
                        'video_name': os.path.basename(video_file),
                        'score': score
                    })
    except Exception as exc:
        logging.exception("Error while scanning target directory: %s", exc)
    return pairs

def perform_deletion(pairs: List[Dict], dry_run: bool = True, use_trash: bool = True, auto_confirm: bool = False) -> Tuple[int, int]:
    """
    Delete (or trash) the given pairs. Returns counts (folders_deleted, videos_deleted).
    """
    if not pairs:
        logging.info("No pairs to delete.")
        return 0, 0

    logging.info("Pairs to delete: %d", len(pairs))
    folders_deleted = 0
    videos_deleted = 0

    if not dry_run:
        if not auto_confirm:
            print("\n⚠️  This will permanently remove or move to trash the listed items.")
            confirm = input("Type 'YES' to proceed: ").strip()
            if confirm.upper() != 'YES':
                logging.info("User cancelled deletion.")
                return 0, 0

    for pair in pairs:
        # Delete folder
        try:
            if dry_run:
                logging.info("[DRY-RUN] Would delete folder: %s", pair['folder_path'])
            else:
                if use_trash and SEND_TO_TRASH_AVAILABLE:
                    send2trash(pair['folder_path'])
                else:
                    shutil.rmtree(pair['folder_path'])
                logging.info("Deleted folder: %s", pair['folder'])
                folders_deleted += 1
        except Exception as exc:
            logging.exception("Failed to delete folder %s: %s", pair['folder_path'], exc)

        # Delete video
        try:
            if dry_run:
                logging.info("[DRY-RUN] Would delete video: %s", pair['video_file'])
            else:
                if use_trash and SEND_TO_TRASH_AVAILABLE:
                    send2trash(pair['video_file'])
                else:
                    os.remove(pair['video_file'])
                logging.info("Deleted video: %s", pair['video_name'])
                videos_deleted += 1
        except Exception as exc:
            logging.exception("Failed to delete video %s: %s", pair['video_file'], exc)

    return folders_deleted, videos_deleted

# ---------------------------
# Debug / preview
# ---------------------------
def debug_matching(folder_name: str, downloads_directory: str, debug_limit: int = 10):
    """Print debug info for a single folder using the current index."""
    index = index_videos(downloads_directory)
    fc = extract_core_name(folder_name)
    print(f"\nDEBUG: folder='{folder_name}' -> core='{fc}'")
    for filename in list(index.keys())[:debug_limit]:
        vc = extract_core_name(filename)
        sc = similarity_score(fc, vc)
        if sc > 0.2:
            print(f"  candidate: '{filename}' core='{vc}' score={sc:.2f}")

# ---------------------------
# CLI
# ---------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Delete .gifs folders only when matching video files exist.")
    parser.add_argument('--target', '-t', default=r"C:\Users\harip\ALL TEST", help="Target directory to scan for .gifs folders")
    parser.add_argument('--downloads', '-d', default=r"D:\downloads", help="Directory containing video files")
    parser.add_argument('--threshold', type=float, default=0.65, help="Similarity threshold (0-1) for a match to count")
    parser.add_argument('--dry-run', action='store_true', help="Preview only; do not delete anything")
    parser.add_argument('--yes', action='store_true', help="Skip interactive confirmation")
    parser.add_argument('--no-trash', action='store_true', help="Do not use send2trash even if available; delete permanently")
    parser.add_argument('--log', default='clean_pairs.log', help="Path to log file")
    return parser.parse_args()

def setup_logging(log_path: str):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def main():
    args = parse_args()
    setup_logging(args.log)
    logging.info("Started clean_pairs.py")

    if not os.path.isdir(args.target):
        logging.error("Target directory not found: %s", args.target)
        print(f"Target directory not found: {args.target}")
        return

    if not os.path.isdir(args.downloads):
        logging.error("Downloads directory not found: %s", args.downloads)
        print(f"Downloads directory not found: {args.downloads}")
        return

    pairs = gather_pairs(args.target, args.downloads, threshold=args.threshold)

    if not pairs:
        print("❌ No matching pairs found with current thresholds.")
        logging.info("No matching pairs found.")
        # Optionally show debug for up to 3 folders
        sample_folders = [f for f in os.listdir(args.target) if os.path.isdir(os.path.join(args.target, f)) and f.lower().endswith('.gifs')][:3]
        if sample_folders:
            print("\n💡 Running debug on up to first 3 .gifs folders:")
            for f in sample_folders:
                debug_matching(f, args.downloads)
        return

    print(f"\n🎯 WOULD DELETE ({len(pairs)} pairs):")
    for i, p in enumerate(pairs, 1):
        print(f"  {i}. {p['folder']}  ->  {p['video_name']} (score: {p['score']:.2f})")

    if args.dry_run:
        print("\n🔍 Dry run enabled — no files will be deleted.")
    else:
        print("\n⚠️ This operation will delete the listed items.")
        if SEND_TO_TRASH_AVAILABLE and not args.no_trash:
            print("  Files will be moved to Trash/Recycle Bin (send2trash available).")
        else:
            print("  Files will be permanently deleted (send2trash unavailable or --no-trash used).")

    folders_deleted, videos_deleted = perform_deletion(
        pairs,
        dry_run=args.dry_run,
        use_trash=(not args.no_trash) and SEND_TO_TRASH_AVAILABLE,
        auto_confirm=args.yes
    )

    print("\n📊 Summary")
    print("=" * 30)
    print(f"Folders deleted: {folders_deleted}")
    print(f"Videos deleted: {videos_deleted}")
    logging.info("Completed: folders_deleted=%d videos_deleted=%d", folders_deleted, videos_deleted)

if __name__ == '__main__':
    main()
