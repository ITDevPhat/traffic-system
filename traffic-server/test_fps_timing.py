"""
🧪 Test FPS Timing - Kiểm tra video có chạy đúng tốc độ không
"""

import cv2
import time
import os

def test_video_timing(video_path):
    """Test thời gian chạy video thực tế"""
    
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return
    
    # Get video info
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_seconds = total_frames / fps if fps > 0 else 0
    
    print(f"📹 Video: {video_path}")
    print(f"📊 FPS: {fps:.2f}")
    print(f"🎬 Total frames: {total_frames}")
    print(f"⏱️  Expected duration: {duration_seconds:.2f}s ({duration_seconds/60:.1f} min)")
    
    # Test reading with pacing
    frame_interval = 1.0 / fps if fps > 0 else 0.033
    print(f"🎯 Frame interval: {frame_interval:.3f}s")
    
    start_time = time.perf_counter()
    last_frame_time = start_time
    frame_count = 0
    
    print("\n🚀 Starting paced reading test...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Pacing - sleep to maintain FPS
        now = time.perf_counter()
        dt = now - last_frame_time
        if dt < frame_interval:
            time.sleep(frame_interval - dt)
            now = time.perf_counter()
        last_frame_time = now
        
        # Progress every 100 frames
        if frame_count % 100 == 0:
            elapsed = now - start_time
            current_fps = frame_count / elapsed if elapsed > 0 else 0
            progress = (frame_count / total_frames) * 100
            print(f"📊 Frame {frame_count}/{total_frames} ({progress:.1f}%) - "
                  f"Elapsed: {elapsed:.1f}s - Current FPS: {current_fps:.2f}")
    
    end_time = time.perf_counter()
    total_elapsed = end_time - start_time
    actual_fps = frame_count / total_elapsed if total_elapsed > 0 else 0
    
    print(f"\n✅ Test completed!")
    print(f"📊 Frames processed: {frame_count}")
    print(f"⏱️  Total time: {total_elapsed:.2f}s")
    print(f"🎯 Actual FPS: {actual_fps:.2f}")
    print(f"📈 Speed ratio: {actual_fps/fps:.2f}x" if fps > 0 else "N/A")
    
    if abs(actual_fps - fps) < 1.0:
        print("✅ Timing is accurate!")
    else:
        print("⚠️  Timing deviation detected!")
    
    cap.release()

if __name__ == "__main__":
    # Test với video hiện có
    test_videos = [
        "videos/video.mp4",
        "videos/video2.mp4", 
        "videos/video3.mp4",
        "videos/video4.mp4"
    ]
    
    for video in test_videos:
        if os.path.exists(video):
            test_video_timing(video)
            print("-" * 60)
            break